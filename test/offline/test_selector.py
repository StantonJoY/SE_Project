"""selector 解析与闭集选择的离线测试。

Verifies: REQ-ADS-ARCH-002（闭集选择）、REQ-ADS-ARCH-003（输出必须为合法结构化 JSON）、
          REQ-ADS-ARCH-004（确定性可复现）、
          INV-ADS-002（AI 绝不在候选集之外选择）、INV-ADS-003（非法输出绝不进入决策）。
批准：docs/test-approvals.yaml 的 TA-0002（按 docs/plans/P4-selector.md §4 预先批准）。
运行：仓库根目录下 pytest test/offline/test_selector.py
"""

from __future__ import annotations

import json

import pytest

from selector import LLMClient, LLMUnavailable, MockLLM, OutputJudgment, parse_llm_output
from selector.parser import LLMOutputError

CANDS = ["ad_001", "ad_002", "ad_003"]


def _raw(ad_id: str, reason: str = "理由", confidence: float = 0.8) -> str:
    return json.dumps({"ad_id": ad_id, "reason": reason, "confidence": confidence})


# ---- REQ-ADS-ARCH-003：合法输出 ----

def test_parse_valid_json_ok() -> None:
    """REQ-ADS-ARCH-003：合法 JSON 必须解析为 OutputJudgment。"""
    j = parse_llm_output(_raw("ad_002", "因为场景匹配", 0.75), CANDS)
    assert isinstance(j, OutputJudgment)
    assert j.ad_id == "ad_002"
    assert j.reason == "因为场景匹配"
    assert j.confidence == pytest.approx(0.75)


def test_parse_accepts_confidence_bounds() -> None:
    """REQ-ADS-ARCH-003：confidence 的闭区间端点 [0,1] 必须被接受。"""
    assert parse_llm_output(_raw("ad_001", confidence=0.0), CANDS).confidence == 0.0
    assert parse_llm_output(_raw("ad_001", confidence=1.0), CANDS).confidence == 1.0


# ---- INV-ADS-002：闭集 gate ----

def test_parse_rejects_out_of_candidates() -> None:
    """INV-ADS-002（反例）：候选集外的 ad_id 必须被拒绝，且不得被"纠正"为最接近的候选。"""
    with pytest.raises(LLMOutputError, match="不在候选集内"):
        parse_llm_output(_raw("ad_999"), CANDS)


def test_parse_rejects_empty_candidate_set() -> None:
    """INV-ADS-002（反例）：候选集为空时，任何 ad_id 都必须被拒绝。"""
    with pytest.raises(LLMOutputError, match="不在候选集内"):
        parse_llm_output(_raw("ad_001"), [])


# ---- INV-ADS-003：fail-closed 的各类畸形输入 ----

def test_parse_rejects_malformed_json() -> None:
    """INV-ADS-003（反例）：非 JSON 文本必须被拒绝（fail-closed）。"""
    with pytest.raises(LLMOutputError, match="不是合法 JSON"):
        parse_llm_output("ad_001 我选这个", CANDS)


def test_parse_rejects_top_level_not_object() -> None:
    """INV-ADS-003（反例）：顶层非 JSON 对象必须被拒绝。"""
    with pytest.raises(LLMOutputError, match="顶层必须是 JSON 对象"):
        parse_llm_output(json.dumps(["ad_001"]), CANDS)


def test_parse_rejects_missing_fields() -> None:
    """INV-ADS-003（反例）：缺必需字段必须被拒绝。"""
    with pytest.raises(LLMOutputError, match="缺必需字段"):
        parse_llm_output(json.dumps({"ad_id": "ad_001", "reason": "理由"}), CANDS)


def test_parse_rejects_extra_fields() -> None:
    """INV-ADS-003（反例）：未声明的多余字段必须被拒绝（防 LLM 注入控制字段）。"""
    payload = {"ad_id": "ad_001", "reason": "理由", "confidence": 0.8, "override": True}
    with pytest.raises(LLMOutputError, match="多余字段"):
        parse_llm_output(json.dumps(payload), CANDS)


def test_parse_rejects_wrong_field_types() -> None:
    """INV-ADS-003（反例）：字段类型错误必须被拒绝。"""
    with pytest.raises(LLMOutputError, match="ad_id 必须是非空字符串"):
        parse_llm_output(json.dumps({"ad_id": "", "reason": "r", "confidence": 0.5}), CANDS)
    with pytest.raises(LLMOutputError, match="reason 必须是字符串"):
        parse_llm_output(json.dumps({"ad_id": "ad_001", "reason": 1, "confidence": 0.5}), CANDS)


def test_parse_rejects_boolean_confidence() -> None:
    """INV-ADS-003（反例）：bool 是 int 的子类，必须显式排除，不得被当作 1/0。"""
    with pytest.raises(LLMOutputError, match="confidence 必须是数值"):
        parse_llm_output(json.dumps({"ad_id": "ad_001", "reason": "r", "confidence": True}), CANDS)


def test_parse_rejects_confidence_out_of_range() -> None:
    """INV-ADS-003（反例）：confidence 越界 [0,1] 必须被拒绝。"""
    with pytest.raises(LLMOutputError, match=r"必须落在 \[0,1\]"):
        parse_llm_output(_raw("ad_001", confidence=1.01), CANDS)
    with pytest.raises(LLMOutputError, match=r"必须落在 \[0,1\]"):
        parse_llm_output(_raw("ad_001", confidence=-0.01), CANDS)


def test_parse_rejects_non_string_raw() -> None:
    """INV-ADS-003（反例）：非字符串的原始输出必须被拒绝。"""
    with pytest.raises(LLMOutputError, match="必须是字符串"):
        parse_llm_output(None, CANDS)  # type: ignore[arg-type]


# ---- REQ-ADS-ARCH-004：确定性 ----

def test_parse_is_deterministic() -> None:
    """REQ-ADS-ARCH-004：同一输入重复解析必须得到逐位一致的结果。"""
    raw = _raw("ad_003", "同一理由", 0.42)
    results = [parse_llm_output(raw, CANDS) for _ in range(5)]
    assert all(r == results[0] for r in results)


def test_mock_llm_deterministic() -> None:
    """REQ-ADS-ARCH-004：MockLLM 同输入同输出（无随机、无时钟依赖）。"""
    prompt = "## RETRIEVED\n- ad_003 | retail | 标题 | tags: -\n- ad_001 | retail | 标题 | tags: -"
    first = MockLLM().select(prompt)
    assert all(MockLLM().select(prompt) == first for _ in range(5))
    # 只从 prompt 中出现的候选中挑，且取字典序最小（确定性规则）
    assert parse_llm_output(first, ["ad_001", "ad_003"]).ad_id == "ad_001"


def test_mock_llm_without_candidates_yields_empty_ad_id() -> None:
    """INV-ADS-003：prompt 中无候选时，MockLLM 产出空 ad_id —— 必被 parser 的 fail-closed 拦住。

    parser 的检查顺序为「非空字符串」先于「候选集存在性」，故此处命中的是前者。
    两者都属 fail-closed，具体命中哪一条由顺序固定（该顺序本身由端到端集成测试约束）。
    """
    raw = MockLLM().select("## RETRIEVED\n（无候选）")
    with pytest.raises(LLMOutputError, match="ad_id 必须是非空字符串"):
        parse_llm_output(raw, CANDS)


def test_parse_rejects_nonempty_ad_id_absent_from_candidates() -> None:
    """INV-ADS-002（反例）：格式合法但不在候选集内的 ad_id 必须被拒绝。

    与上一条互补：那条覆盖"空 ad_id"，本条覆盖"格式对但集外"，
    确保闭集 gate 在**两个不同前置条件下**都被行使。
    """
    with pytest.raises(LLMOutputError, match="不在候选集内"):
        parse_llm_output(_raw("ad_777"), CANDS)


def test_mock_llm_can_inject_failure() -> None:
    """REQ-ADS-ARCH-004 / ADR-002 D1：MockLLM 可注入失败，用于测试降级路径。"""
    client = MockLLM(fail_with=LLMUnavailable("超时"))
    with pytest.raises(LLMUnavailable):
        client.select("任意")


def test_mock_llm_satisfies_protocol() -> None:
    """REQ-ADS-ARCH-002：MockLLM 必须满足 LLMClient 协议（可替换性）。"""
    assert isinstance(MockLLM(), LLMClient)


def test_mock_llm_raw_override_passthrough() -> None:
    """INV-ADS-003：raw_override 必须原样返回，使畸形输出可被构造与测试。"""
    assert MockLLM(raw_override="not json{").select("x") == "not json{"
