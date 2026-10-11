"""输出契约的离线测试。

Verifies: REQ-ADS-FR-004（两形态输出且均通过 schema 校验）。
批准：docs/test-approvals.yaml 的 TA-0003（⚠️ 批准晚于实现，见 TD-023）。
运行：仓库根目录下 pytest test/offline/test_render.py
"""

from __future__ import annotations

import json

import pytest

from render import (
    RENDER_SCHEMA,
    AdPayload,
    AdRenderResult,
    DegradeReason,
    NoAdRenderResult,
    render_ad,
    render_no_ad,
    to_json,
    validate_render,
)


def an_ad(**over) -> AdRenderResult:
    kw = {
        "ad_id": "ad_001",
        "title": "深夜咖啡外卖",
        "copy": "加班夜，一杯热美式送到家",
        "category": "food_delivery",
        "explanation": "因为场景匹配",
        "explanation_degraded": False,
        "confidence": 0.85,
        "audit_id": "aud-abc123",
    }
    kw.update(over)
    return render_ad(**kw)


# ---- 广告形态 ----

def test_ad_form_passes_schema() -> None:
    """REQ-ADS-FR-004：广告形态必须通过 render schema。"""
    assert validate_render(an_ad()) == []


def test_ad_form_carries_audit_id() -> None:
    """REQ-ADS-GOV-001：展示的广告必须携带审计 ID（可追溯）。"""
    r = an_ad()
    assert r.audit_id == "aud-abc123"
    assert r.ad == AdPayload("ad_001", "深夜咖啡外卖", "加班夜，一杯热美式送到家", "food_delivery")


def test_ad_form_rejects_bad_ad_id_pattern() -> None:
    """REQ-ADS-FR-004（反例）：ad_id 不符合 `ad_<数字>` 时 schema 必须报错。"""
    errors = validate_render(an_ad(ad_id="not-an-ad"))
    assert errors, "非法 ad_id 应被 schema 拒绝"


def test_ad_form_rejects_confidence_out_of_range() -> None:
    """REQ-ADS-FR-004（反例）：confidence 越界时 schema 必须报错。"""
    assert validate_render(an_ad(confidence=1.5))
    assert validate_render(an_ad(confidence=-0.1))


def test_ad_form_rejects_empty_title() -> None:
    """REQ-ADS-FR-004（反例）：空标题不得通过（展示空白广告是无意义输出）。"""
    assert validate_render(an_ad(title=""))


# ---- 无广告形态 ----

def test_no_ad_form_passes_schema() -> None:
    """REQ-ADS-FR-004：无广告形态必须通过 render schema。"""
    r = render_no_ad(reason=DegradeReason.NO_CANDIDATES, detail="候选为空", audit_id="aud-x")
    assert validate_render(r) == []
    assert r.kind == "no_ad"
    assert r.reason_code == "no_candidates"


@pytest.mark.parametrize("reason", list(DegradeReason))
def test_every_degrade_reason_is_in_schema(reason: DegradeReason) -> None:
    """REQ-ADS-FR-003：**每一个**降级原因码都必须被 schema 接受。

    本测试保证"新增原因码却忘改 schema"会立刻失败（枚举与 schema 不漂移）。
    """
    r = render_no_ad(reason=reason, audit_id="aud-y")
    assert validate_render(r) == [], f"{reason.value} 不在 RENDER_SCHEMA 的 enum 中"


def test_no_ad_rejects_unknown_reason_code() -> None:
    """REQ-ADS-FR-003（反例）：未登记的原因码必须被 schema 拒绝。

    这使"原因码是封闭枚举"成为机器可验证的性质，而非约定。
    """
    r = NoAdRenderResult(kind="no_ad", reason_code="some_new_reason", audit_id="aud-z")
    assert validate_render(r), "未登记的原因码应被 schema 拒绝"


def test_no_ad_metadata_not_exposed() -> None:
    """REQ-ADS-GOV-001：审计用 metadata **不得**进入对外渲染结果。"""
    r = render_no_ad(
        reason=DegradeReason.LOW_CONFIDENCE,
        detail="confidence 0.3 < 0.5",
        audit_id="aud-m",
        metadata={"confidence": 0.3, "internal_note": "不应外泄"},
    )
    d = r.to_dict()
    assert "metadata" not in d
    assert "internal_note" not in json.dumps(d)
    # 但对象上仍保留（供审计写入）
    assert r.metadata["confidence"] == 0.3


# ---- 序列化 ----

def test_to_json_is_deterministic_and_utf8() -> None:
    """REQ-ADS-ARCH-004：序列化必须确定性，且中文不被转义（可读性）。"""
    r = an_ad()
    once, twice = to_json(r), to_json(r)
    assert once == twice
    assert "深夜咖啡外卖" in once
    assert "\\u" not in once


def test_to_json_round_trips() -> None:
    """REQ-ADS-FR-004：序列化结果必须可被解析回等价数据。"""
    r = an_ad()
    back = json.loads(to_json(r))
    assert back["kind"] == "ad"
    assert back["ad"]["ad_id"] == "ad_001"
    assert validate_render(r) == []


def test_schema_is_a_union_of_two_forms() -> None:
    """REQ-ADS-FR-004：schema 必须是两形态的判别联合（kind 为判别键）。"""
    assert "oneOf" in RENDER_SCHEMA
    kinds = {
        branch["properties"]["kind"].get("const")
        for branch in RENDER_SCHEMA["oneOf"]
    }
    assert kinds == {"ad", "no_ad"}
