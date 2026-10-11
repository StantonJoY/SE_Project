"""六层上下文装配与 token 预算（ASR-ADS-A3-01）。

Implements: ADR-001（AI 看到什么由架构控制，不由模型自行累积）
            ASR-ADS-A3-01（课程 §3.3.1：token budget 是架构性的）
Enforces: INV-ADS-014（上下文预算绝不被突破；standing constraints 绝不因压缩而消失）
Verifies: REQ-ADS-NFR-COST-001（token 上限于配置单一来源）

对应课程 §8.4（P163–165）：
  · **六层提示架构**：SYSTEM / INSTRUCTIONS / RETRIEVED / HISTORY / STATE / USER
  · **五步装配管线**：DEDUPLICATE → PRIORITIZE → BUDGET → COMPACT → ASSEMBLE
  · **85% 处 compaction**，且 compaction 后**必须重新注入**层 2 的 standing constraints

**本项目的关键差异**（`memory-design.md` §4 M3）：V1 是无状态单轮，
HISTORY 层**恒为空**，compaction 的触发源**只有"单轮上下文过大"**（主要是候选集规模），
不可能来自"历史累积"。HISTORY 层仍**显式存在**并标注"不适用 + 理由"——
省略会让后来者误以为忘了做，显式声明才让"这是一个决定"可被审计。

确定性：`count_tokens` 与全部装配逻辑均为纯函数（无时钟、无随机、无 locale 依赖）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .client import briefs_to_prompt_block
from .types import AssembledContext, BudgetDecision, BudgetMode, CandidateBrief

# ---- 六层名称（顺序即装配顺序） ----
LAYER_SYSTEM = "SYSTEM"
LAYER_INSTRUCTIONS = "INSTRUCTIONS"
LAYER_RETRIEVED = "RETRIEVED"
LAYER_HISTORY = "HISTORY"
LAYER_STATE = "STATE"
LAYER_USER = "USER"
LAYER_NAMES: tuple[str, ...] = (
    LAYER_SYSTEM,
    LAYER_INSTRUCTIONS,
    LAYER_RETRIEVED,
    LAYER_HISTORY,
    LAYER_STATE,
    LAYER_USER,
)

# 永不裁剪的层（课程：System / Instructions 永不裁剪）
NEVER_TRIMMED: frozenset[str] = frozenset({LAYER_SYSTEM, LAYER_INSTRUCTIONS})

DEFAULT_BUDGET_TOKENS = 2000
COMPACTION_THRESHOLD_RATIO = 0.85

# 六层 prompt 模板的版本号（REQ-ADS-AI-002 的版本溯源字段之一）。
# 语义：**模板结构**变化时递增（层级增删、standing constraints 改写、渲染顺序调整）。
# 普通文案微调不改版本号，除非影响约束的表述。
# 该常量由 `app.pipeline` 写审计记录的 `provenance.prompt_version`。
PROMPT_TEMPLATE_VERSION = "ctx-v1"

# HISTORY 在 V1 的显式声明（不得默默省略）
HISTORY_NOT_APPLICABLE = (
    "[HISTORY — 不适用] V1 为无状态单轮推荐，不存在对话或轮次历史；"
    "该层恒为空。理由见 docs/architecture/memory-design.md §3。"
)

# 层 2 的 standing constraints —— **compaction 后必须重新注入**
# 内容即闭集与权威边界的最小陈述（INV-ADS-002 / INV-ADS-004）。
STANDING_CONSTRAINTS = (
    "约束（不可协商）：\n"
    "1) 只能从候选列表中选择 ad_id，不得输出列表之外的任何广告；\n"
    "2) 不得自创或改写广告文案；\n"
    "3) 必须输出 JSON，字段恰为 ad_id / reason / confidence，不得增减字段；\n"
    "4) 你的输出仅为建议，是否展示由确定性合规层裁决。"
)

SYSTEM_PROMPT = (
    "你是场景化广告推荐系统的候选选择器，"
    "职责是在给定场景与候选集内选择一条最合适的广告并说明理由。"
    "你不拥有展示与否的最终决定权。"
)

# 注入标记：重注入后用它断言层 2 确实回到了最终 prompt 中
REINJECTION_MARKER = "约束（不可协商）："


def count_tokens(text: str) -> int:
    """确定性 token 数**估算**（纯函数）：`ceil(len(text) / 3)`。

    保守估算：本项目文本以中文为主，3 字符/token 偏保守（实际通常更少），
    用它做预算校验不会低估成本。**刻意不引入 tiktoken 等依赖**——
    真实 tokenizer 属 P8 接真实 LLM 时的决定；届时若更换估算方式，
    须同步更新本函数与本模块测试。
    """
    return math.ceil(len(text) / 3)


def route_budget(
    estimated_tokens: int,
    budget: int = DEFAULT_BUDGET_TOKENS,
    *,
    threshold_ratio: float = COMPACTION_THRESHOLD_RATIO,
) -> BudgetDecision:
    """三档确定性路由（ASR-ADS-14 / RP-010）。

    · `<= threshold` → `DIRECT`（直接装配）
    · `<= budget`    → `SUMMARIZE`（压缩候选摘要后再装配）
    · 否则           → `OVER_BUDGET`（上层应降级为 `no_ad`，原因码 `budget_exceeded`）
    """
    if budget <= 0:
        raise ValueError(f"budget 必须为正整数，实际为 {budget}")
    threshold = int(budget * threshold_ratio)
    if estimated_tokens <= threshold:
        mode = BudgetMode.DIRECT
    elif estimated_tokens <= budget:
        mode = BudgetMode.SUMMARIZE
    else:
        mode = BudgetMode.OVER_BUDGET
    return BudgetDecision(
        mode=mode,
        estimated_tokens=estimated_tokens,
        budget=budget,
        compaction_threshold=threshold,
    )


@dataclass
class _Assembler:
    """一次装配的可变工作区（每次 assemble 独立新建，避免实例状态）。"""

    budget_tokens: int
    threshold_ratio: float
    summarize_n: int
    layers: dict[str, str] = field(default_factory=dict)
    decisions: list[str] = field(default_factory=list)
    compacted: bool = False

    # ---- 步骤 1：DEDUPLICATE ----
    def deduplicate(self, candidates: list[CandidateBrief]) -> list[CandidateBrief]:
        seen: set[str] = set()
        out: list[CandidateBrief] = []
        dropped = 0
        for c in candidates:
            if c.ad_id in seen:
                dropped += 1
                continue
            seen.add(c.ad_id)
            out.append(c)
        if dropped:
            self.decisions.append(f"DEDUPLICATE: 去除 {dropped} 条重复候选")
        return out

    # ---- 步骤 2：PRIORITIZE ----
    def prioritize(self, candidates: list[CandidateBrief]) -> list[CandidateBrief]:
        # 按 ad_id 升序 = 确定性排序（不依赖输入顺序，便于逐位复现）
        ordered = sorted(candidates, key=lambda c: c.ad_id)
        if [c.ad_id for c in ordered] != [c.ad_id for c in candidates]:
            self.decisions.append("PRIORITIZE: 候选按 ad_id 升序重排（确定性）")
        return ordered

    # ---- 步骤 4：COMPACT ----
    def compact_candidates(
        self, candidates: list[CandidateBrief], mode: BudgetMode
    ) -> list[CandidateBrief]:
        """SUMMARIZE 档：保留前 N 条（已确定性排序），其余折叠为计数。"""
        if mode is not BudgetMode.SUMMARIZE or len(candidates) <= self.summarize_n:
            return candidates
        self.compacted = True
        kept = candidates[: self.summarize_n]
        self.decisions.append(
            f"COMPACT: 候选摘要 {len(candidates)} → {len(kept)} 条（SUMMARIZE 档）"
        )
        return kept

    # ---- 步骤 5：ASSEMBLE（含重注入） ----
    def build_layers(
        self,
        scene_summary: str,
        candidates: list[CandidateBrief],
        task: str,
        total_candidates: int,
    ) -> None:
        block = briefs_to_prompt_block(candidates)
        if len(candidates) < total_candidates:
            block += f"\n（另有 {total_candidates - len(candidates)} 条候选因预算被折叠，未列出）"

        self.layers[LAYER_SYSTEM] = SYSTEM_PROMPT
        self.layers[LAYER_INSTRUCTIONS] = STANDING_CONSTRAINTS
        self.layers[LAYER_RETRIEVED] = block or "（无候选）"
        self.layers[LAYER_HISTORY] = HISTORY_NOT_APPLICABLE
        self.layers[LAYER_STATE] = f"[场景] {scene_summary}"
        self.layers[LAYER_USER] = task

        # **重注入**：无论是否发生 compaction，层 2 都必须在最终 prompt 中出现。
        # 这不是"可选优化"——课程 P165 实测 compaction 会把 Instructions 推到
        # 低注意力位置，导致"规则存在但不可见"（约束满足率 98% → 72%）。
        if self.compacted:
            self.layers[LAYER_INSTRUCTIONS] = (
                STANDING_CONSTRAINTS + "\n（本约束已在上下文压缩后重新注入）"
            )
            self.decisions.append("RE-INJECT: compaction 后重新注入层 2 standing constraints")

    def render(self) -> str:
        """按优先级顺序拼接为单一 prompt。"""
        parts = [f"## {name}\n{self.layers[name]}" for name in LAYER_NAMES]
        return "\n\n".join(parts)


class ContextAssembler:
    """六层上下文装配器（无状态；每次 `assemble` 独立，可重复调用且逐位一致）。

    Args:
        budget_tokens: 上下文 token 上限（单一来源：`config.yaml`）。
        threshold_ratio: compaction 触发比例，默认 0.85。
        summarize_candidates: SUMMARIZE 档保留的候选条数。
    """

    def __init__(
        self,
        *,
        budget_tokens: int = DEFAULT_BUDGET_TOKENS,
        threshold_ratio: float = COMPACTION_THRESHOLD_RATIO,
        summarize_candidates: int = 5,
    ) -> None:
        self._budget_tokens = budget_tokens
        self._threshold_ratio = threshold_ratio
        self._summarize_n = summarize_candidates

    @property
    def budget_tokens(self) -> int:
        return self._budget_tokens

    def assemble(
        self,
        scene_summary: str,
        candidates: list[CandidateBrief],
        task: str,
    ) -> AssembledContext:
        """按五步管线装配六层上下文，返回结果与其可审计决策记录。"""
        w = _Assembler(
            budget_tokens=self._budget_tokens,
            threshold_ratio=self._threshold_ratio,
            summarize_n=self._summarize_n,
        )

        total = len(candidates)
        # ① DEDUPLICATE → ② PRIORITIZE
        cands = w.prioritize(w.deduplicate(candidates))

        # ③ BUDGET（先按未压缩规模估算）
        probe = _Assembler(  # 仅用于估算，避免污染真实决策记录
            budget_tokens=self._budget_tokens,
            threshold_ratio=self._threshold_ratio,
            summarize_n=self._summarize_n,
        )
        probe.build_layers(scene_summary, cands, task, total)
        decision = route_budget(
            count_tokens(probe.render()), self._budget_tokens, threshold_ratio=self._threshold_ratio
        )
        w.decisions.append(
            f"BUDGET: 估算 {decision.estimated_tokens} token / 预算 {decision.budget}"
            f"（阈值 {decision.compaction_threshold}）→ {decision.mode.value}"
        )

        # ④ COMPACT（按路由结果决定是否压缩）
        cands = w.compact_candidates(cands, decision.mode)

        # ⑤ ASSEMBLE（含重注入）
        w.build_layers(scene_summary, cands, task, total)
        prompt = w.render()
        tokens = count_tokens(prompt)

        if tokens > self._budget_tokens:
            w.decisions.append(
                f"OVER_BUDGET: 装配后 {tokens} token 超过预算 {self._budget_tokens}"
                "——上层应降级为 no_ad（RP-010）"
            )

        return AssembledContext(
            prompt=prompt,
            layers=dict(w.layers),
            compacted=w.compacted,
            tokens=tokens,
            decisions=tuple(w.decisions),
        )
