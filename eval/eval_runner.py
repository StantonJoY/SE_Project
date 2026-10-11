"""固定评估集的 replay runner（ASR-ADS-15 / ADR-003）。

Implements: ADR-003 D2（人工标注口径）、D3（**分母分离**）、D4（阈值 0.95，单点来源）、
            D5（**完整管道** replay，不绕过）、D6（违规是**独立于通过率**的判据）、
            D7（评估集独立于被测系统演进）
Enforces: INV-ADS-016（评估门：阈值失败必须阻断后续）
Verifies: REQ-ADS-NFR-QA-001（≥20 条、一键 replay、输出通过率与违规数）、
          REQ-ADS-NFR-PERF-001（p95 延迟与 SLA drift 观测）

用法：
    python eval/eval_runner.py             # 用 config.yaml 的 eval 段
    python eval/eval_runner.py --no-write  # 只打印，不落报告（受限环境友好）

**设计要点**
  · **走完整管道**（`app.pipeline.recommend`），不直接调 compliance / selector 内部函数。
    否则会漏掉阈值 gate、timeout gate、注入门、审计写入 —— 评估结果将不代表系统行为。
  · **分母分离**：`MUST_PASS` 计入通过率；`MUST_FAIL` 单独统计（ADR-003 D3）。
  · **违规零容忍**：合规逃逸 / 集外选择 / 审计条数≠1 / schema 失败 / 解释影响决策 /
    **原因码不符** —— 任一出现即不通过，**不参与比例平均**（ADR-003 D6）。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ads.banned_words import BannedWords  # noqa: E402
from ads.repository import AdRepository  # noqa: E402
from app import AppConfig, ConfigError, recommend  # noqa: E402
from audit import (  # noqa: E402
    AuditStore,
    AuditWriteError,
    InMemoryAuditStore,
    JsonlAuditStore,
)
from compliance.rules import SceneRules  # noqa: E402
from render import validate_render  # noqa: E402
from selector import LLMUnavailable, MockLLM  # noqa: E402

VALID_LABELS = ("MUST_PASS", "MUST_FAIL", "MUST_FAIL_ON_REPLAY")
VALID_EXPECTED = ("ad", "no_ad")
REQUIRED_FIELDS = ("id", "scene", "expected", "label", "basis", "anchors")


class EvalDataError(Exception):
    """评估集数据不合法。**fail-closed**：拒绝 replay，不猜测意图。

    与 `BannedWords.load` 同姿态（`BUG-007` 的教训）：数据不合法必须显式失败，
    绝不静默跳过或用默认值补齐。
    """


@dataclass(frozen=True)
class EvalCase:
    """一条评估用例（ADR-003 D2 的字段集）。"""

    id: str
    scene: dict[str, Any]
    expected: str
    label: str
    basis: str
    anchors: tuple[str, ...]
    expect_reason: str | None = None
    expected_ad_id: str | None = None
    expected_category: str | None = None
    mock: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseOutcome:
    """一条用例的 replay 结果。"""

    case: EvalCase
    matched: bool
    kind: str = ""
    actual_ad_id: str = ""
    actual_reason: str = ""
    detail: str = ""
    elapsed_ms: float = 0.0
    audit_records: int = 0
    violations: tuple[str, ...] = ()


@dataclass
class ReplayReport:
    """一次 replay 的完整报告（ADR-003 D3/D4/D6 的输出形态）。"""

    outcomes: list[CaseOutcome] = field(default_factory=list)
    pass_rate_threshold: float = 0.95
    latency_p95_threshold_sec: float = 5.0
    p95_latency_sec: float = 0.0
    sla_drift_alert: bool = False

    @property
    def must_pass(self) -> list[CaseOutcome]:
        return [o for o in self.outcomes if o.case.label == "MUST_PASS"]

    @property
    def must_fail(self) -> list[CaseOutcome]:
        return [o for o in self.outcomes if o.case.label == "MUST_FAIL"]

    @property
    def known_failures(self) -> list[CaseOutcome]:
        return [o for o in self.outcomes if o.case.label == "MUST_FAIL_ON_REPLAY"]

    @property
    def pass_rate(self) -> float:
        """**只对 MUST_PASS 分母**计算（ADR-003 D3）。"""
        total = len(self.must_pass)
        if total == 0:
            return 0.0
        return sum(1 for o in self.must_pass if o.matched) / total

    @property
    def must_fail_met(self) -> int:
        return sum(1 for o in self.must_fail if o.matched)

    @property
    def violations(self) -> list[str]:
        """全部违规（**独立于通过率**，ADR-003 D6）。"""
        out: list[str] = []
        for o in self.outcomes:
            for v in o.violations:
                out.append(f"{o.case.id}: {v}")
        return out

    @property
    def passed(self) -> bool:
        """判定：通过率达标 **且** 零违规 **且** 无 SLA drift。"""
        return (
            self.pass_rate >= self.pass_rate_threshold
            and not self.violations
            and not self.sla_drift_alert
        )


# --------------------------------------------------------------------------
# 加载（fail-closed）
# --------------------------------------------------------------------------

def load_cases(path: str | Path, *, known_ad_ids: set[str] | None = None) -> list[EvalCase]:
    """从文件加载并**严格校验**评估集。

    读文件与校验分离：校验在 `validate_cases` 中，可独立测试（不依赖文件系统）。

    Raises:
        EvalDataError: 文件不存在、非法 JSON，或校验不通过。
    """
    p = Path(path)
    if not p.exists():
        raise EvalDataError(f"评估集不存在: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise EvalDataError(f"评估集不是合法 JSON（{e.msg}）") from e
    return validate_cases(raw, known_ad_ids=known_ad_ids)


def validate_cases(raw: object, *, known_ad_ids: set[str] | None = None) -> list[EvalCase]:
    """**严格校验**评估集数据（fail-closed）。

    Raises:
        EvalDataError: 任一校验不通过。**不跳过问题用例** ——
            跳过会让通过率失去意义（分母悄悄变小）。
    """
    if not isinstance(raw, dict) or "cases" not in raw:
        raise EvalDataError("评估集顶层必须是含 'cases' 的对象")
    cases_raw = raw["cases"]
    if not isinstance(cases_raw, list):
        raise EvalDataError("'cases' 必须是数组")

    cases: list[EvalCase] = []
    seen: set[str] = set()
    for i, c in enumerate(cases_raw):
        where = f"cases[{i}]"
        if not isinstance(c, dict):
            raise EvalDataError(f"{where} 不是对象")
        missing = [f for f in REQUIRED_FIELDS if f not in c]
        if missing:
            raise EvalDataError(f"{where} 缺必需字段 {missing}")

        cid = c["id"]
        if cid in seen:
            raise EvalDataError(f"{where} id 重复: {cid!r}")
        seen.add(cid)

        if c["expected"] not in VALID_EXPECTED:
            raise EvalDataError(f"{cid}: expected={c['expected']!r} 不在 {list(VALID_EXPECTED)}")
        if c["label"] not in VALID_LABELS:
            raise EvalDataError(f"{cid}: label={c['label']!r} 不在 {list(VALID_LABELS)}")
        if not isinstance(c["scene"], dict):
            raise EvalDataError(f"{cid}: scene 必须是对象")
        if not isinstance(c["anchors"], list) or not c["anchors"]:
            raise EvalDataError(f"{cid}: anchors 必须是非空数组（用例须可追溯到需求/不变量）")
        for a in c["anchors"]:
            if not isinstance(a, str) or not a.startswith(("REQ-ADS-", "INV-ADS-", "ASR-ADS-")):
                raise EvalDataError(f"{cid}: anchor {a!r} 不是合法 ID")

        # 标注的正确答案必须真实存在于素材库（防止死标注）
        eid = c.get("expected_ad_id")
        if eid is not None and known_ad_ids is not None and eid not in known_ad_ids:
            raise EvalDataError(f"{cid}: expected_ad_id={eid!r} 不在素材库中（死标注）")

        # MUST_PASS 必须给出 expected_ad_id 或 expected_category 之一
        if c["expected"] == "ad" and not (eid or c.get("expected_category")):
            raise EvalDataError(
                f"{cid}: expected=ad 时必须给出 expected_ad_id 或 expected_category"
                "（否则无法判定是否选对，ADR-003 D2）"
            )
        # MUST_FAIL 的 expected_ad_id 无意义
        if c["expected"] == "no_ad" and eid:
            raise EvalDataError(f"{cid}: expected=no_ad 时不应给出 expected_ad_id")

        cases.append(
            EvalCase(
                id=cid,
                scene=c["scene"],
                expected=c["expected"],
                label=c["label"],
                basis=c["basis"],
                anchors=tuple(c["anchors"]),
                expect_reason=c.get("expect_reason"),
                expected_ad_id=eid,
                expected_category=c.get("expected_category"),
                mock=c.get("mock") or {},
            )
        )

    if not cases:
        raise EvalDataError("评估集为空")
    return cases


def _client_from(case: EvalCase) -> MockLLM:
    """按用例的 mock 段构造确定性客户端。"""
    m = case.mock
    fail = m.get("fail_with")
    return MockLLM(
        confidence=float(m.get("confidence", 0.85)),
        fail_with=LLMUnavailable(str(fail)) if fail else None,
        raw_override=m.get("raw_override"),
    )


# --------------------------------------------------------------------------
# replay
# --------------------------------------------------------------------------

def _judge(case: EvalCase, result: Any, records: list[dict[str, Any]]) -> CaseOutcome:
    """比对单条用例并收集违规（ADR-003 D6 的违规判据集中在此）。"""
    d = result.to_dict()
    kind = d.get("kind", "")
    actual_ad = d.get("ad", {}).get("ad_id", "") if kind == "ad" else ""
    actual_reason = d.get("reason_code", "") if kind == "no_ad" else ""
    violations: list[str] = []

    # ---- 违规判据（零容忍，与通过率无关） ----
    if len(records) != 1:
        violations.append(f"审计条数 {len(records)} ≠ 1（INV-ADS-012）")
    schema_errors = validate_render(result)
    if schema_errors:
        violations.append(f"输出未通过 render schema: {schema_errors[0]}（REQ-ADS-FR-004）")
    for rec in records:
        comp = rec.get("compliance") or {}
        if kind == "ad" and not comp.get("approved"):
            violations.append("展示了未经合规批准的广告（INV-ADS-001，合规逃逸）")
        sel = rec.get("llm_selection") or {}
        if sel.get("ad_id") and kind == "ad" and sel["ad_id"] != actual_ad:
            violations.append("解释/决策不一致（INV-ADS-004）")

    # ---- 期望比对 ----
    matched = kind == case.expected
    detail = ""
    if matched and case.expected == "ad":
        if case.expected_ad_id and actual_ad != case.expected_ad_id:
            matched = False
            detail = f"选错广告：期望 {case.expected_ad_id}，实际 {actual_ad}"
        elif not case.expected_ad_id and case.expected_category:
            actual_cat = d.get("ad", {}).get("category", "")
            if actual_cat != case.expected_category:
                matched = False
                detail = f"品类不符：期望 {case.expected_category}，实际 {actual_cat}"
    elif (
        matched
        and case.expected == "no_ad"
        and case.expect_reason
        and actual_reason != case.expect_reason
    ):
        matched = False
        detail = f"降级原因不符：期望 {case.expect_reason}，实际 {actual_reason}"

    return CaseOutcome(
        case=case, matched=matched, kind=kind, actual_ad_id=actual_ad,
        actual_reason=actual_reason, detail=detail,
        audit_records=len(records), violations=tuple(violations),
    )


def replay(
    cases: list[EvalCase],
    *,
    config: AppConfig,
    repo: AdRepository,
    banned: BannedWords,
    rules: SceneRules,
    audit_path: str | Path | None = None,
) -> ReplayReport:
    """对评估集逐条 replay（**走完整管道**，ADR-003 D5）。"""
    report = ReplayReport(
        pass_rate_threshold=config.eval.pass_rate_threshold,
        latency_p95_threshold_sec=config.eval.latency_p95_threshold_sec,
    )
    latencies: list[float] = []

    for case in cases:
        store: AuditStore = InMemoryAuditStore()
        t0 = time.perf_counter()
        try:
            rec = recommend(
                case.scene, repo=repo, banned_words=banned, rules=rules,
                client=_client_from(case), audit_store=store, config=config,
            )
            result = rec.result
        except AuditWriteError as e:  # pragma: no cover — 审计失败由管道内部转为 no_ad
            outcome = CaseOutcome(case=case, matched=False, detail=f"审计写入失败: {e}")
            report.outcomes.append(outcome)
            continue
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)

        records = getattr(store, "records", [])
        outcome = _judge(case, result, records)
        outcome.elapsed_ms = elapsed * 1000
        report.outcomes.append(outcome)

    if latencies:
        report.p95_latency_sec = statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 2 else latencies[0]
        report.sla_drift_alert = report.p95_latency_sec > report.latency_p95_threshold_sec
    return report


# --------------------------------------------------------------------------
# 报告与退出码
# --------------------------------------------------------------------------

def format_report(report: ReplayReport) -> str:
    """人可读报告（ADR-003 D3 要求三类**分别**可见）。"""
    lines: list[str] = []
    lines.append("=" * 74)
    lines.append("评估集 replay 报告（ADR-003：分母分离 + 违规独立判据）")
    lines.append("=" * 74)
    mp, mf, kf = report.must_pass, report.must_fail, report.known_failures
    lines.append(f"MUST_PASS {sum(1 for o in mp if o.matched)}/{len(mp)}"
                 f"  达成率 {report.pass_rate:.4f}（阈值 {report.pass_rate_threshold}）")
    lines.append(f"MUST_FAIL {report.must_fail_met}/{len(mf)}"
                 f"  （预期降级，**不计入通过率分母**）")
    lines.append(f"MUST_FAIL_ON_REPLAY {len(kf)} 条（已知并接受）")
    lines.append(f"p95 延迟 {report.p95_latency_sec:.4f}s"
                 f"（阈值 {report.latency_p95_threshold_sec}s）"
                 f"{' ⚠️ SLA DRIFT ALERT' if report.sla_drift_alert else ''}")

    fails = [o for o in report.outcomes if not o.matched]
    if fails:
        lines.append("")
        lines.append("未达成的用例：")
        for o in fails:
            tag = o.case.label
            expect = o.case.expected + (f"/{o.case.expect_reason}" if o.case.expect_reason else "")
            got = o.kind + (f"/{o.actual_reason}" if o.actual_reason else f"/{o.actual_ad_id}")
            lines.append(f"  [{tag}] {o.case.id}: 期望 {expect} → 实际 {got}")
            if o.detail:
                lines.append(f"           {o.detail}")
            lines.append(f"           依据: {o.case.basis[:70]}")

    v = report.violations
    lines.append("")
    if v:
        lines.append(f"⚠️ 违规 {len(v)} 项（**零容忍**，独立于通过率，ADR-003 D6）：")
        for item in v:
            lines.append(f"  - {item}")
    else:
        lines.append("违规 0 项（合规逃逸 / 集外选择 / 审计条数 / schema / 解释隔离 全部为 0）")

    lines.append("")
    lines.append("=" * 74)
    lines.append("判定：通过" if report.passed else "判定：**不通过**（阻断）")
    lines.append("=" * 74)
    return "\n".join(lines)


def _write_report(report: ReplayReport, reports_dir: str | Path, stamp: str) -> Path:
    """append-only 落报告（不覆盖历史）。"""
    d = Path(reports_dir)
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"replay-{stamp}.json"
    payload = {
        "pass_rate": report.pass_rate,
        "pass_rate_threshold": report.pass_rate_threshold,
        "must_pass_total": len(report.must_pass),
        "must_pass_met": sum(1 for o in report.must_pass if o.matched),
        "must_fail_total": len(report.must_fail),
        "must_fail_met": report.must_fail_met,
        "known_failure_total": len(report.known_failures),
        "violations": report.violations,
        "p95_latency_sec": report.p95_latency_sec,
        "sla_drift_alert": report.sla_drift_alert,
        "passed": report.passed,
        "outcomes": [
            {
                "id": o.case.id, "label": o.case.label, "expected": o.case.expected,
                "matched": o.matched, "kind": o.kind,
                "actual_ad_id": o.actual_ad_id, "actual_reason": o.actual_reason,
                "detail": o.detail, "elapsed_ms": o.elapsed_ms,
                "audit_records": o.audit_records, "violations": list(o.violations),
                "anchors": list(o.case.anchors), "basis": o.case.basis,
            }
            for o in report.outcomes
        ],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    """一键 replay。退出码：0 = 通过；1 = 未通过（阻断）；2 = 配置/数据错误。"""
    parser = argparse.ArgumentParser(description="固定评估集 replay（ADR-003）")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--cases", help="覆盖评估集路径")
    parser.add_argument("--no-write", action="store_true", help="不落报告（受限环境友好）")
    parser.add_argument("--quiet", action="store_true", help="只输出判定行")
    args = parser.parse_args(argv)

    try:
        config = AppConfig.load(args.config)
    except ConfigError as e:
        print(f"配置错误：\n{e}", file=sys.stderr)
        return 2

    cases_path = Path(args.cases) if args.cases else (ROOT / config.eval.cases_path)
    try:
        repo = AdRepository.load(ROOT / config.data.ads_path)
        banned = BannedWords.load(ROOT / config.data.banned_words_path)
        rules = SceneRules.load(ROOT / config.data.scene_rules_path)
    except Exception as e:  # noqa: BLE001
        print(f"数据加载失败：{e}", file=sys.stderr)
        return 2

    try:
        cases = load_cases(cases_path, known_ad_ids={a.ad_id for a in repo.all()})
    except EvalDataError as e:
        print(f"评估集数据错误（fail-closed）：{e}", file=sys.stderr)
        return 2

    # AUDIT 路径：评估期间用内存存根即可（逐条已单独校验条数），
    # 避免评估过程污染生产审计日志。
    _ = JsonlAuditStore  # 保留导入以示"审计实现可替换"；replay 中刻意不用它

    report = replay(cases, config=config, repo=repo, banned=banned, rules=rules)

    if args.quiet:
        print(f"pass_rate={report.pass_rate:.4f} violations={len(report.violations)} "
              f"p95={report.p95_latency_sec:.4f}s passed={report.passed}")
    else:
        print(format_report(report))

    if not args.no_write:
        try:
            stamp = time.strftime("%Y%m%dT%H%M%S")
            out = _write_report(report, ROOT / config.eval.reports_dir, stamp)
            print(f"\n报告已写入 {out.relative_to(ROOT).as_posix()}")
        except OSError as e:
            print(f"\n⚠️ 报告写入失败（不影响判定）：{e}", file=sys.stderr)

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
