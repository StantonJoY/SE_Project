"""selector 的共享数据形状（frozen dataclass）。

Implements: ADR-001（AI 建议层的数据契约）
Verifies: REQ-ADS-ARCH-003（输出必须为合法结构化 JSON → 解析后即为本模块的形状）

独立成模块的理由：`client` / `parser` / `context` / `explanation` 四方共享这些形状，
若定义在任一方内部会造成循环导入。形状集中于此，不依赖任何其它 selector 模块。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class CandidateBrief:
    """喂给 LLM 的候选广告摘要（**只读**视图）。

    刻意不直接传 `ads.models.Ad`：候选集必须以**裁剪后的摘要**进入上下文，
    否则会把素材的全部字段（含 `scene_restrictions` 等）暴露给 LLM，
    既浪费 token 又扩大了它"自作主张"的空间。
    """

    ad_id: str
    title: str
    category: str
    target_tags: tuple[str, ...] = ()


class BudgetMode(str, Enum):
    """`route_budget` 的三档确定性路由（ASR-ADS-14 / RP-010）。"""

    DIRECT = "DIRECT"          # 预算内，直接装配
    SUMMARIZE = "SUMMARIZE"    # 接近上限，压缩候选摘要
    OVER_BUDGET = "OVER_BUDGET"  # 即使压缩仍超上限 → 上层应降级 no_ad


@dataclass(frozen=True)
class BudgetDecision:
    """`route_budget` 的产出。"""

    mode: BudgetMode
    estimated_tokens: int
    budget: int
    compaction_threshold: int  # 达到该值即触发 compaction（默认 85% 预算）


@dataclass(frozen=True)
class OutputJudgment:
    """LLM 的**已校验**结构化输出（REQ-ADS-ARCH-003）。

    只有通过 `parse_llm_output` 的严格校验才会产生本对象——
    因此持有本对象即意味着：字段齐备、类型正确、confidence ∈ [0,1]、
    且 `ad_id` **确在候选集内**（INV-ADS-002）。
    """

    ad_id: str
    reason: str
    confidence: float


@dataclass(frozen=True)
class AssembledContext:
    """六层上下文的装配结果（ASR-ADS-A3-01 / INV-ADS-014）。"""

    prompt: str
    layers: dict[str, str]
    compacted: bool
    tokens: int
    decisions: tuple[str, ...] = field(default_factory=tuple)
    """装配过程的可审计记录（去重命中、压缩了哪层、是否重注入等）。"""


@dataclass(frozen=True)
class Explanation:
    """解释路径的产出（INV-ADS-004）。

    口径（`OQ-009`，2026-10-06 确认）= **「为什么选这条广告」**：
    须说明在当前场景下为何选该广告而非候选集中的其他广告。
    """

    ad_id: str
    text: str
    degraded: bool = False
    """解释质量不达标或含违禁词时为 True —— 此时只降级解释，**`ad_id` 不变**。"""
