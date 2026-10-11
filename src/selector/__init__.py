"""AI 建议层（selector）—— LLM 闭集选择 + 严格输出解析 + 上下文装配 + 解释路径。

Implements: ADR-001（Guarded Hybrid：AI 解释，代码裁决）
            ADR-002 D1（失败语义：超时/异常 → 由上层降级为 no_ad）
Enforces: INV-ADS-002（AI 绝不在候选集之外选择）
          INV-ADS-003（非法 LLM 输出绝不进入决策）
          INV-ADS-004（解释路径绝不影响决策）
          INV-ADS-014（上下文预算绝不被突破；关键约束绝不因压缩而消失）
Verifies: REQ-ADS-ARCH-002 / 003 / 004、REQ-ADS-NFR-COST-001、REQ-ADS-AI-001

**权威级别：Advisory only。** 本包不产出"展示或不展示"的裁决——那是
`compliance.pipeline` 的职责（FINAL AUTHORITY）。本包只产出**建议**，
且建议必须经过 `compliance` 才能变为展示。**本包不得导入 compliance**
（反向依赖会倒置权威边界，见 concern-clusters.md §0 的簇分离）。
"""

from __future__ import annotations

from .client import LLMClient, LLMUnavailable, MockLLM
from .context import (
    LAYER_NAMES,
    PROMPT_TEMPLATE_VERSION,
    AssembledContext,
    BudgetDecision,
    BudgetMode,
    ContextAssembler,
    count_tokens,
    route_budget,
)
from .explanation import (
    Explanation,
    ExplanationVerdict,
    generate_explanation,
    verify_explanation,
)
from .parser import LLMOutputError, OutputJudgment, parse_llm_output
from .types import CandidateBrief

__all__ = [
    # 建议层入口
    "LLMClient",
    "MockLLM",
    "LLMUnavailable",
    # 解析（闭集的执行点）
    "parse_llm_output",
    "OutputJudgment",
    "LLMOutputError",
    # 上下文装配
    "ContextAssembler",
    "CandidateBrief",
    "AssembledContext",
    "BudgetDecision",
    "BudgetMode",
    "LAYER_NAMES",
    "PROMPT_TEMPLATE_VERSION",
    "route_budget",
    "count_tokens",
    # 解释路径
    "generate_explanation",
    "verify_explanation",
    "Explanation",
    "ExplanationVerdict",
]
