"""渲染结果的构造与序列化。

Implements: ADR-002 D1（降级终态为结构化 no_ad）
Verifies: REQ-ADS-FR-004（两形态均通过 schema 校验）

`render_ad` / `render_no_ad` 是**唯一的**结果构造入口 —— 管道不得自行拼 dict。
这样"输出符合 schema"是结构性质（构造即合法），而非事后校验的期望。
"""

from __future__ import annotations

import json
from typing import Any

from .schema import (
    AdPayload,
    AdRenderResult,
    DegradeReason,
    NoAdRenderResult,
    RenderResult,
)


def render_ad(
    *,
    ad_id: str,
    title: str,
    copy: str,
    category: str,
    explanation: str,
    explanation_degraded: bool,
    confidence: float,
    audit_id: str,
) -> AdRenderResult:
    """构造广告形态的渲染结果（APPROVE 路径）。"""
    return AdRenderResult(
        kind="ad",
        ad=AdPayload(ad_id=ad_id, title=title, copy=copy, category=category),
        explanation=explanation,
        explanation_degraded=explanation_degraded,
        confidence=confidence,
        audit_id=audit_id,
    )


def render_no_ad(
    *,
    reason: DegradeReason,
    detail: str = "",
    audit_id: str = "",
    attempts: int = 1,
    metadata: dict[str, Any] | None = None,
) -> NoAdRenderResult:
    """构造无广告形态的渲染结果（任一降级路径）。

    Args:
        reason: 降级原因码（封闭枚举，见 `DegradeReason`）。
        detail: 面向诊断的补充说明。
        audit_id: 审计记录 ID，使"没广告"也能被追溯。
        attempts: LLM 调用/解析的尝试次数（用于诊断与统计）。
        metadata: 审计用补充信息，**不进入对外输出**。
    """
    return NoAdRenderResult(
        kind="no_ad",
        reason_code=reason.value,
        detail=detail,
        audit_id=audit_id,
        attempts=attempts,
        metadata=metadata or {},
    )


def to_json(result: RenderResult, *, indent: int | None = None) -> str:
    """序列化为 JSON 文本（确定性：键顺序由 dataclass 定义顺序固定）。"""
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=indent)
