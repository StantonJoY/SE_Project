"""输出契约：广告形态与无广告形态（REQ-ADS-FR-004）。

Implements: ADR-002 D1（降级终态 no_ad 是结构化结果，不是异常）
Verifies: REQ-ADS-FR-004（渲染输出结构化结果，两形态均通过 schema 校验）

两种形态：
  · `Ad{RenderResult}`   —— APPROVE：含广告内容、解释、置信度、审计 ID
  · `NoAdRenderResult`   —— 任何降级：含**原因码**（可诊断，不含模糊措辞）

设计要点：`reason_code` 取值为封闭枚举（`DegradeReason`），
使"降级原因可统计"成为结构性质，而非靠解析自由文本。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class DegradeReason(str, Enum):
    """降级原因码（对应 docs/architecture/runtime-policy-catalog.md 的各条策略）。

    成员与 RP 策略一一对应；新增成员须同时新增/更新对应策略条目。
    """

    SCENE_INVALID = "scene_invalid"              # RP-002 场景输入非法
    NO_CANDIDATES = "no_candidates"              # RP-008 候选集为空
    INJECTION_DETECTED = "injection_detected"    # RP-003 注入检出
    BUDGET_EXCEEDED = "budget_exceeded"          # RP-010 上下文超预算
    LLM_TIMEOUT = "llm_timeout"                  # RP-009 LLM 超时
    LLM_ERROR = "llm_error"                      # RP-009 LLM 调用异常
    LLM_OUTPUT_INVALID = "llm_output_invalid"    # RP-004 输出非法（重试后仍失败）
    LOW_CONFIDENCE = "low_confidence"            # RP-006 低置信度
    COMPLIANCE_REJECTED = "compliance_rejected"  # RP-007 合规过滤拒绝
    AUDIT_WRITE_FAILURE = "audit_write_failure"  # RP-011 审计失败 → 整体失败


@dataclass(frozen=True)
class AdPayload:
    """被选中的广告（展示所需的最小字段，不含素材内部字段）。"""

    ad_id: str
    title: str
    copy: str
    category: str


@dataclass(frozen=True)
class AdRenderResult:
    """广告形态：展示一条广告。"""

    kind: str = "ad"
    ad: AdPayload | None = None
    explanation: str = ""
    explanation_degraded: bool = False
    confidence: float = 0.0
    audit_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NoAdRenderResult:
    """无广告形态：不展示任何广告，但给出**可诊断的原因码**。"""

    kind: str = "no_ad"
    reason_code: str = ""
    detail: str = ""
    audit_id: str = ""
    attempts: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    """审计用补充信息（如实际 confidence、候选集规模），**不进入用户可见输出**。"""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # 审计用元数据不进入对外渲染结果 —— 用户只需知道"没广告"与原因码
        d.pop("metadata", None)
        return d


RenderResult = AdRenderResult | NoAdRenderResult

# 对外 schema（两种形态的判别联合）——用于 REQ-ADS-FR-004 的校验
RENDER_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [
        {
            "type": "object",
            "required": ["kind", "ad", "explanation", "confidence", "audit_id"],
            "additionalProperties": False,
            "properties": {
                "kind": {"const": "ad"},
                "ad": {
                    "type": "object",
                    "required": ["ad_id", "title", "copy", "category"],
                    "additionalProperties": False,
                    "properties": {
                        "ad_id": {"type": "string", "pattern": "^ad_[0-9]+$"},
                        "title": {"type": "string", "minLength": 1},
                        "copy": {"type": "string", "minLength": 1},
                        "category": {"type": "string", "minLength": 1},
                    },
                },
                "explanation": {"type": "string"},
                "explanation_degraded": {"type": "boolean"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "audit_id": {"type": "string"},
            },
        },
        {
            "type": "object",
            "required": ["kind", "reason_code", "audit_id"],
            "additionalProperties": False,
            "properties": {
                "kind": {"const": "no_ad"},
                "reason_code": {
                    "type": "string",
                    "enum": [r.value for r in DegradeReason],
                },
                "detail": {"type": "string"},
                "audit_id": {"type": "string"},
                "attempts": {"type": "integer", "minimum": 0},
            },
        },
    ],
}


def validate_render(result: RenderResult) -> list[str]:
    """校验渲染结果符合 `RENDER_SCHEMA`；返回错误列表（空 = 通过）。

    刻意**不引入 jsonschema 之外的新依赖**，且两形态共用同一 schema 定义。
    """
    import jsonschema

    errors: list[str] = []
    try:
        jsonschema.validate(instance=result.to_dict(), schema=RENDER_SCHEMA)
    except jsonschema.ValidationError as e:
        where = "/".join(str(p) for p in e.absolute_path) or "<root>"
        errors.append(f"{where}: {e.message}")
    return errors
