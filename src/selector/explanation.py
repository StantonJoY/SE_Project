"""解释路径——与决策路径结构分离（ASR-ADS-A3-02 / INV-ADS-004）。

Implements: ADR-001 §2（解释路径只读；AI 只在解释层面获胜）
            ASR-ADS-A3-02（课程 §3.3.2 Explanation Quality 是架构性的）
Enforces: INV-ADS-004（解释路径绝不影响决策；解释不得绕过合规 gate）
Verifies: REQ-ADS-AI-001、REQ-ADS-ARCH-002

**口径**（`OQ-009`，2026-10-06 由人类确认）= **「为什么选这条广告」**：
解释须说明在当前场景特征下，为何选择该广告**而非候选集中的其他广告**。

**结构隔离的三条实现手段**（不是靠文档承诺）：
  1. `generate_explanation` 的返回类型不含任何可写决策的句柄；
  2. `verify_explanation` 的**签名里根本没有 `ad_id` 参数** ——
     它无法改写决策，因为调用方**没有把 ad_id 交给它**；
  3. 全部降级路径都返回 `verdict="degraded"`，且降级文本**不携带**新的 ad_id。

「解释失败 ≠ 决策失败」（课程 §3.3.2）：本模块的任何失败都**不**改变选择结果。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ads.banned_words import BannedWords

from .types import CandidateBrief, Explanation, OutputJudgment

# 解释质量下限：低于此长度视为"未说明理由"，降级为结构化摘要
MIN_EXPLANATION_CHARS = 8

NEUTRAL_FALLBACK = "（解释不可用：已降级为结构化摘要，不影响本次选择结果。）"


@dataclass(frozen=True)
class ExplanationVerdict:
    """解释校验结果。

    **注意本类型刻意不含 `ad_id`**：解释路径产出的一切都不得携带可改写决策的信息。
    调用方在需要展示时，自行把原始 `judgment.ad_id` 与 `text` 组合。
    """

    verdict: Literal["ok", "degraded"]
    text: str
    reason_code: str  # ok / too_short / banned_word

    @property
    def degraded(self) -> bool:
        return self.verdict == "degraded"


def generate_explanation(
    judgment: OutputJudgment,
    candidates: list[CandidateBrief],
) -> Explanation:
    """产出解释文本（口径：为什么选这条广告）。

    本函数**只读**：不写任何外部状态，不修改 `judgment`（frozen dataclass）。
    为满足口径，它会引用**候选集中的其他广告**作为对照。

    Args:
        judgment: 已校验的 LLM 选择（含 reason 与 confidence）。
        candidates: 本次候选集（用于对照说明"为何不是其他候选"）。

    Returns:
        `Explanation`（含 `ad_id`，便于展示时与决策配对）。
    """
    others = [c for c in candidates if c.ad_id != judgment.ad_id]
    chosen = next((c for c in candidates if c.ad_id == judgment.ad_id), None)

    parts: list[str] = []
    if chosen is not None:
        parts.append(f"选择 {chosen.ad_id}（品类 {chosen.category}）的理由：{judgment.reason}")
    else:
        # 候选集中找不到该 ad_id —— 不应发生（parser 已保证闭集），保守处理
        parts.append(f"选择 {judgment.ad_id} 的理由：{judgment.reason}")
    parts.append(f"置信度 {judgment.confidence:.2f}。")
    if others:
        others_desc = "、".join(f"{c.ad_id}({c.category})" for c in others[:5])
        more = f" 等 {len(others)} 条" if len(others) > 5 else ""
        parts.append(f"在同一场景下，候选集中还有 {others_desc}{more}，但它们的品类或目标标签与本场景的匹配度更低。")
    else:
        parts.append("候选集中没有其他可选广告。")

    return Explanation(ad_id=judgment.ad_id, text="".join(parts), degraded=False)


def verify_explanation(
    explanation: Explanation,
    banned_words: BannedWords,
) -> ExplanationVerdict:
    """校验解释文本；违规时**剥离**解释（降级为结构化摘要）。

    **签名刻意不含 `ad_id`** —— 本函数在结构上不可能改写决策（INV-ADS-004）。

    校验项：
      · 长度不足 `MIN_EXPLANATION_CHARS` → `too_short`（未真正说明理由）
      · 命中违禁词 → `banned_word`（防止解释成为绕过合规 gate 的泄漏渠道）

    任一项失败 → `verdict="degraded"`，`text` 替换为 `NEUTRAL_FALLBACK`。
    本函数**只读**：不修改传入的 `explanation`。

    Args:
        explanation: `generate_explanation` 的产出。
        banned_words: 违禁词表（`ads.banned_words.BannedWords`）。

    Returns:
        `ExplanationVerdict`（不含 ad_id）。
    """
    text = explanation.text

    hit = banned_words.check(text)
    if hit is not None:
        return ExplanationVerdict(
            verdict="degraded",
            text=NEUTRAL_FALLBACK,
            reason_code="banned_word",
        )

    if len(text.strip()) < MIN_EXPLANATION_CHARS:
        return ExplanationVerdict(
            verdict="degraded",
            text=NEUTRAL_FALLBACK,
            reason_code="too_short",
        )

    return ExplanationVerdict(verdict="ok", text=text, reason_code="ok")
