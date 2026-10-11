"""渲染输出模块。

Implements: ADR-002 D1（降级终态为结构化 no_ad，不是异常）
Verifies: REQ-ADS-FR-004（两形态均通过 schema 校验）

模块边界（架构元素 ⑤「输出契约」）：
  · `schema.py`  —— 两形态的数据结构与判别联合 schema
  · `serializer.py` —— 结果构造与序列化（本模块的对外入口）
"""

from __future__ import annotations

from .schema import (
    RENDER_SCHEMA,
    AdPayload,
    AdRenderResult,
    DegradeReason,
    NoAdRenderResult,
    RenderResult,
    validate_render,
)
from .serializer import (
    render_ad,
    render_no_ad,
    to_json,
)

__all__ = [
    # 数据结构
    "RenderResult",
    "AdRenderResult",
    "NoAdRenderResult",
    "AdPayload",
    "DegradeReason",
    "RENDER_SCHEMA",
    # 入口
    "render_ad",
    "render_no_ad",
    "to_json",
    "validate_render",
]
