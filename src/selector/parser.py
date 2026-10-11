"""LLM 输出的严格解析——**闭集选择的执行点**。

Implements: ADR-001 §2（AI 之后必须有确定性 validation gate）
            ADR-002 D1（解析失败 → 重试 1 次 → 降级 no_ad）
Enforces: INV-ADS-003（不符合输出 schema 的 LLM 输出绝不被当作有效选择）
          INV-ADS-002（LLM 返回的 ad_id 绝不出现在候选集之外）
Verifies: REQ-ADS-ARCH-003（输出必须为合法结构化 JSON）、REQ-ADS-ARCH-002（闭集）

**fail-closed**：以下任一情形均抛 `LLMOutputError`，由上层重试 1 次后降级为 `no_ad`——
非 JSON / 顶层非对象 / 缺字段 / 字段类型错 / 多余字段 / `ad_id` 为空 /
`confidence` 非数值或越界 [0,1] / **`ad_id` 不在候选集内**。

不做"纠正"：绝不把集外 `ad_id` 替换为"最接近的候选"——那会破坏闭集不变量的语义。
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from .types import OutputJudgment

# 输出 schema：**额外字段一律拒绝**（防止 LLM 注入未声明的控制字段）
REQUIRED_FIELDS = ("ad_id", "reason", "confidence")


class LLMOutputError(Exception):
    """LLM 输出不合法（格式 / 字段 / 取值范围 / 候选集存在性）。"""


def _reject(reason: str) -> LLMOutputError:
    return LLMOutputError(f"LLM 输出不合法（REQ-ADS-ARCH-003）: {reason}")


def parse_llm_output(raw: str, candidate_ids: Sequence[str]) -> OutputJudgment:
    """把 LLM 的原始文本严格解析为 `OutputJudgment`。

    Args:
        raw: LLM 返回的原始文本。
        candidate_ids: 本次允许的候选 `ad_id` 集合（闭集）。

    Returns:
        已校验的 `OutputJudgment`。

    Raises:
        LLMOutputError: 任一校验不通过。**调用方必须降级，不得继续展示。**
    """
    if not isinstance(raw, str):
        raise _reject(f"原始输出必须是字符串，实际为 {type(raw).__name__}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise _reject(f"不是合法 JSON（{e.msg}）") from e

    if not isinstance(data, dict):
        raise _reject(f"顶层必须是 JSON 对象，实际为 {type(data).__name__}")

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise _reject(f"缺必需字段 {missing}")
    extra = sorted(set(data) - set(REQUIRED_FIELDS))
    if extra:
        raise _reject(f"含未声明的多余字段 {extra}")

    ad_id = data["ad_id"]
    reason = data["reason"]
    confidence = data["confidence"]

    if not isinstance(ad_id, str) or not ad_id.strip():
        raise _reject(f"ad_id 必须是非空字符串，实际为 {ad_id!r}")
    if not isinstance(reason, str):
        raise _reject(f"reason 必须是字符串，实际为 {type(reason).__name__}")
    # bool 是 int 的子类，须显式排除，否则 True/False 会被当成 1/0
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise _reject(f"confidence 必须是数值，实际为 {type(confidence).__name__}")
    if not (0.0 <= float(confidence) <= 1.0):
        raise _reject(f"confidence 必须落在 [0,1]，实际为 {confidence}")

    # ---- 闭集 gate：INV-ADS-002 的执行点 ----
    allowed = set(candidate_ids)
    if ad_id not in allowed:
        raise _reject(f"ad_id {ad_id!r} 不在候选集内（候选 {sorted(allowed)}）")

    return OutputJudgment(ad_id=ad_id, reason=reason, confidence=float(confidence))
