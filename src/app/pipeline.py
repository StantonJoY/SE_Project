"""推荐管道编排（REQ-ADS-FR-003 的 fallback path 集合）。

Implements: ADR-001（AI 建议 → 确定性裁决的接线）
            ADR-002 D1（降级终态统一为 no_ad）、D2（审计失败 → 整体失败）
            concern-clusters.md §0（C1 强制层与 C5 降级层**不可混**）
Enforces: INV-ADS-001（未经合规过滤的广告绝不被展示）
          INV-ADS-012（每次请求恰好 1 条审计证据）
          INV-ADS-013（超时/异常绝不导致崩溃）
Verifies: REQ-ADS-FR-003、REQ-ADS-NFR-SAFETY-005、REQ-ADS-NFR-PERF-001、REQ-ADS-SEC-001

管道顺序（不可颠倒）：
    场景校验 → 预筛 → 装配 → **注入门** → LLM 选择（timeout gate）
    → 严格解析（重试 1 次）→ 阈值判定 → **合规过滤** → 解释 → 渲染 → 审计

**权威边界**：`compliance` 位于 LLM **之后** —— AI 建议之后才是确定性裁决。
本模块是唯一允许同时 import `selector` 与 `compliance` 的地方（编排层）；
`selector` 与 `compliance` 之间**禁止互相依赖**（由 fitness function 的 S2 强制）。

**降级路径全覆盖**（每条对应 runtime-policy-catalog 的一条策略）：
    RP-002 scene_invalid ／ RP-008 no_candidates ／ RP-003 injection_detected
    RP-010 budget_exceeded ／ RP-009 llm_timeout ／ RP-009 llm_error
    RP-004 llm_output_invalid ／ RP-006 low_confidence ／ RP-007 compliance_rejected
    RP-011 audit_write_failure（特殊：审计失败时**仍返回** no_ad，不抛异常给调用方）
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from audit import AuditRecordBuilder, AuditStore, AuditWriteError, MetricSnapshot, new_audit_id
from compliance.pipeline import run_compliance
from compliance.rules import SceneRules
from render import DegradeReason, RenderResult, render_ad, render_no_ad
from scene.parser import SceneInputError, parse_scene
from selector import (
    PROMPT_TEMPLATE_VERSION,
    CandidateBrief,
    ContextAssembler,
    LLMClient,
    LLMUnavailable,
    generate_explanation,
    parse_llm_output,
    verify_explanation,
)
from selector.parser import LLMOutputError

from .config import AppConfig
from .sanitize import scan_for_injection

# 合规管道步骤数（用于审计记录；与 compliance.pipeline 的固定顺序一致）
COMPLIANCE_STEPS = ("output_exists", "banned_words", "banned_check", "category", "scene")

# 版本溯源缺失时的取值（REQ-ADS-AI-002）
# **刻意不用空字符串**：空字符串会把"缺失"伪装成"有值"，
# 使 monitor `decisions_missing_version_provenance` 无法统计到它。
UNKNOWN_VERSION = "unknown"


def _provenance(config: AppConfig) -> dict[str, object]:
    """构造本次决策的版本溯源证据（REQ-ADS-AI-002 / INV-ADS-012）。

    记录三样东西，使 replay 结果可归因到具体配置：
      · `model_version`  —— 实际使用的模型（V1 为 `mock`；P8 接真实 LLM 后为真实模型名）
      · `prompt_version` —— 六层 prompt 模板版本（`selector.context.PROMPT_TEMPLATE_VERSION`）
      · `thresholds`     —— 影响本次决策的关键阈值（confidence / token 预算 / timeout / 重试）

    缺失一律写 `"unknown"`，**绝不写空字符串**——缺失必须显式可见、可被统计。
    """
    provider = config.llm.provider or UNKNOWN_VERSION
    model = config.llm.model or ""
    model_version = f"{provider}/{model}" if model else provider
    return {
        "model_version": model_version or UNKNOWN_VERSION,
        "prompt_version": PROMPT_TEMPLATE_VERSION or UNKNOWN_VERSION,
        "thresholds": {
            "confidence_threshold": config.selector.confidence_threshold,
            "context_budget_tokens": config.selector.context_budget_tokens,
            "llm_timeout_sec": config.llm.timeout_sec,
            "max_retries": config.selector.max_retries,
        },
    }


@dataclass(frozen=True)
class Recommendation:
    """一次推荐请求的完整结果（对外的唯一出口）。"""

    result: RenderResult
    audit_id: str


def recommend(
    raw_scene: object,
    *,
    repo: AdRepository,
    banned_words: BannedWords,
    rules: SceneRules,
    client: LLMClient,
    audit_store: AuditStore,
    config: AppConfig,
) -> Recommendation:
    """执行一次推荐：场景 → 建议 → 确定性过滤 → 渲染 + 审计。

    所有依赖显式注入（便于离线测试与替换）；本函数**不读写文件**、
    **不读环境变量**、**不调真实网络**——那些是 `app.cli` 的职责。

    Args:
        raw_scene: 原始场景输入（dict 或等价映射）。
        repo / banned_words / rules: 只读数据源。
        client: AI 建议层（`MockLLM` 或未来的真实客户端）。
        audit_store: 审计存储（写入失败 → 整体失败）。
        config: 不可变运行配置。

    Returns:
        `Recommendation`（含渲染结果与审计 ID）。**不抛业务异常**——
        一切失败都表达为结构化的 `no_ad`。
    """
    audit_id = new_audit_id()
    rec = AuditRecordBuilder(audit_id=audit_id, store=audit_store)
    metrics = MetricSnapshot()
    provenance = _provenance(config)
    rec.add(
        request={"scene": _as_plain(raw_scene)},
        config_source=config.source_path,
        provenance=provenance,   # REQ-ADS-AI-002：每条决策都带版本溯源
    )

    # ---- RP-002 场景输入非法 ----
    try:
        scene = parse_scene(raw_scene)
    except SceneInputError as e:
        return _degrade(rec, metrics, DegradeReason.SCENE_INVALID, str(e), attempts=0)

    rec.add(scene={
        "time_slot": scene.time_slot,
        "device": scene.device,
        "user_tags": list(scene.user_tags),
    })

    # ---- 预筛 → RP-008 候选集为空 ----
    candidates = repo.filter_by_scene(scene)
    rec.add(candidate_count=len(candidates))
    if not candidates:
        return _degrade(rec, metrics, DegradeReason.NO_CANDIDATES, "预筛后候选集为空", attempts=0)

    briefs = [
        CandidateBrief(a.ad_id, a.title, a.category, tuple(a.target_tags))
        for a in candidates
    ]
    # 说明：CandidateBrief 只带 title（不含 copy）—— 候选摘要刻意裁剪，
    # 既省 token，又避免把素材内部字段（scene_restrictions 等）交给 LLM。

    # ---- 装配上下文 ----
    assembler = ContextAssembler(budget_tokens=config.selector.context_budget_tokens)
    ctx = assembler.assemble(
        f"{scene.time_slot}/{scene.device}/{'/'.join(scene.user_tags) or '-'}",
        briefs,
        "请从候选列表中选择一条最适合当前场景的广告，并说明理由。",
    )
    metrics.record("llm_context_tokens_per_request", ctx.tokens)
    metrics.record(
        "post_compaction_constraint_present",
        1 if "约束（不可协商）：" in ctx.prompt else 0,
    )
    rec.add(
        context_tokens=ctx.tokens,
        compacted=ctx.compacted,
        assembly_decisions=list(ctx.decisions),
    )
    if ctx.tokens > config.selector.context_budget_tokens:
        # ---- RP-010 超预算 ----
        return _degrade(
            rec, metrics, DegradeReason.BUDGET_EXCEEDED,
            f"装配后 {ctx.tokens} token 超过预算 {config.selector.context_budget_tokens}",
            attempts=0,
        )

    # ---- RP-003 注入门（pre-model） ----
    scan = scan_for_injection(ctx.prompt)
    if not scan.clean:
        metrics.increment("injection_detected_count")
        rec.add(injection={"pattern_id": scan.pattern_id, "matched": scan.matched_text})
        return _degrade(rec, metrics, DegradeReason.INJECTION_DETECTED, scan.detail, attempts=0)

    # ---- LLM 选择（timeout gate）→ RP-009 ----
    try:
        raw_output = _call_with_timeout(client, ctx.prompt, config.llm.timeout_sec)
    except FuturesTimeout:
        rec.add(llm={"outcome": "timeout", "timeout_sec": config.llm.timeout_sec})
        return _degrade(
            rec, metrics, DegradeReason.LLM_TIMEOUT,
            f"LLM 调用超过 {config.llm.timeout_sec}s", attempts=1,
        )
    except LLMUnavailable as e:
        rec.add(llm={"outcome": "unavailable", "error": str(e)})
        return _degrade(rec, metrics, DegradeReason.LLM_ERROR, str(e), attempts=1)

    rec.add(llm_raw_output=raw_output)

    # ---- 严格解析（重试 1 次）→ RP-004 ----
    candidate_ids = [b.ad_id for b in briefs]
    judgment = None
    attempts = 0
    last_error = ""
    max_attempts = config.selector.max_retries + 1
    for i in range(max_attempts):
        attempts = i + 1
        try:
            judgment = parse_llm_output(raw_output, candidate_ids)
            break
        except LLMOutputError as e:
            last_error = str(e)
    if judgment is None:
        # 注：指标名以 trace-matrix §1 的登记为准（rate，而非 count）——
        # 未登记的指标名会被 MetricSnapshot 拒绝，防止监控口径漂移。
        rec.add(parse={"outcome": "invalid", "attempts": attempts, "error": last_error})
        return _degrade(
            rec, metrics, DegradeReason.LLM_OUTPUT_INVALID, last_error, attempts=attempts,
        )
    rec.add(
        llm_selection={
            "ad_id": judgment.ad_id,
            "confidence": judgment.confidence,
            "attempts": attempts,
        }
    )

    # ---- RP-006 阈值判定 ----
    threshold = config.selector.confidence_threshold
    if judgment.confidence < threshold:
        rec.add(threshold={"value": threshold, "confidence": judgment.confidence, "outcome": "below"})
        return _degrade(
            rec, metrics, DegradeReason.LOW_CONFIDENCE,
            f"confidence {judgment.confidence} < 阈值 {threshold}", attempts=attempts,
            metadata={"confidence": judgment.confidence},
        )

    # ---- RP-007 合规过滤（FINAL AUTHORITY，位于 LLM 之后） ----
    chosen = repo.get(judgment.ad_id)
    if chosen is None:  # 理论上不可能（parser 已保证闭集），保守兜底
        return _degrade(
            rec, metrics, DegradeReason.COMPLIANCE_REJECTED,
            f"选中的 {judgment.ad_id} 不在素材库中", attempts=attempts,
        )
    verdict = run_compliance(chosen, scene, candidates, banned_words, rules)
    rec.add(
        compliance={
            "approved": verdict.approved,
            "rejected_rule": verdict.rejected_rule(),
            "steps": list(COMPLIANCE_STEPS),
        }
    )
    if not verdict.approved:
        failed_rule = verdict.rejected_rule() or "unknown"
        return _degrade(
            rec, metrics, DegradeReason.COMPLIANCE_REJECTED,
            f"合规过滤拒绝（规则 {failed_rule}）: {verdict.detail_of(failed_rule) or ''}".strip(),
            attempts=attempts,
            metadata={"rejected_rule": failed_rule},
        )

    # ---- 解释路径（只读；失败只降级解释） ----
    explanation = generate_explanation(judgment, briefs)
    exp_verdict = verify_explanation(explanation, banned_words)

    # ---- 渲染 ----
    result = render_ad(
        ad_id=chosen.ad_id,
        title=chosen.title,
        copy=chosen.copy,
        category=chosen.category,
        explanation=exp_verdict.text,
        explanation_degraded=exp_verdict.degraded,
        confidence=judgment.confidence,
        audit_id=audit_id,
    )

    # ---- 审计（恰好 1 条；失败 → 整体失败，见 _degrade 的 audit_failed 分支） ----
    rec.add(final={"kind": "ad", "ad_id": chosen.ad_id}, monitors=dict(metrics.values))
    try:
        rec.write()
    except AuditWriteError as e:
        return _audit_failed(metrics, str(e))

    return Recommendation(result=result, audit_id=audit_id)


# --------------------------------------------------------------------------
# 内部辅助
# --------------------------------------------------------------------------

def _call_with_timeout(client: LLMClient, prompt: str, timeout_sec: float) -> str:
    """timeout gate（ADR-002 §2 / REQ-ADS-NFR-PERF-001 的第一个元素）。

    实现说明：用线程池 + `future.result(timeout)`。**已知局限**：
    Python 无法强杀挂起的线程，超时后该线程可能仍在后台（daemon 线程随进程退出）。
    V1 的 `MockLLM` 立即返回，故不受影响；接入真实 LLM（P8）时须改为
    带真实超时的 HTTP 客户端，并在此处记录该局限（见 debt-register）。
    """
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.select, prompt)
        return future.result(timeout=timeout_sec)


def _degrade(
    rec: AuditRecordBuilder,
    metrics: MetricSnapshot,
    reason: DegradeReason,
    detail: str,
    *,
    attempts: int = 1,
    metadata: dict | None = None,
) -> Recommendation:
    """统一降级出口：写**恰好一条**审计记录，返回结构化 `no_ad`。"""
    metrics.increment("no_ad_count")
    rec.add(
        degrade={"reason_code": reason.value, "detail": detail},
        final={"kind": "no_ad", "reason_code": reason.value},
        monitors=dict(metrics.values),
    )
    try:
        rec.write()
    except AuditWriteError as e:
        return _audit_failed(metrics, str(e))
    result = render_no_ad(
        reason=reason, detail=detail, audit_id=rec.audit_id,
        attempts=attempts, metadata=metadata,
    )
    return Recommendation(result=result, audit_id=rec.audit_id)


def _audit_failed(metrics: MetricSnapshot, detail: str) -> Recommendation:
    """审计写入失败路径（RP-011）。

    仍返回结构化的 `no_ad`，但原因码为 `audit_write_failure` ——
    调用方由此得知"这次降级的原因是证据链断了"，而非业务拒绝。
    **不抛异常**：管道对外的契约是"总是返回结构化结果"。
    """
    result = render_no_ad(
        reason=DegradeReason.AUDIT_WRITE_FAILURE,
        detail=f"审计写入失败，推荐整体失败（ADR-002 D2）: {detail}",
        audit_id="",
        attempts=0,
    )
    return Recommendation(result=result, audit_id="")


def _as_plain(raw: object) -> object:
    """把场景输入转成可 JSON 序列化的形式（用于审计记录）。"""
    if isinstance(raw, dict):
        return {str(k): _as_plain(v) for k, v in raw.items()}
    if isinstance(raw, (list, tuple)):
        return [_as_plain(v) for v in raw]
    if isinstance(raw, (str, int, float, bool)) or raw is None:
        return raw
    return repr(raw)
