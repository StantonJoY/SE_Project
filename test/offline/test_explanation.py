"""解释路径隔离的离线测试。

Verifies: REQ-ADS-AI-001（解释必须结构上独立于决策路径）、
          INV-ADS-004（解释路径绝不影响决策；解释不得绕过合规 gate）。
批准：docs/test-approvals.yaml 的 TA-0002（按 docs/plans/P4-selector.md §4 预先批准）。
运行：仓库根目录下 pytest test/offline/test_explanation.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ads.banned_words import BannedWords
from selector import (
    CandidateBrief,
    Explanation,
    ExplanationVerdict,
    OutputJudgment,
    generate_explanation,
    verify_explanation,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

CANDS = [
    CandidateBrief("ad_001", "深夜咖啡外卖", "food_delivery", ("student",)),
    CandidateBrief("ad_004", "AI 编程在线课", "education", ("student",)),
    CandidateBrief("ad_008", "在线视频会员", "subscription", ("student",)),
]


@pytest.fixture
def banned() -> BannedWords:
    return BannedWords.load(DATA_DIR / "banned_words.json")


def judgment(ad_id: str = "ad_001", reason: str = "场景匹配", confidence: float = 0.8) -> OutputJudgment:
    return OutputJudgment(ad_id=ad_id, reason=reason, confidence=confidence)


# ---- REQ-ADS-AI-001：口径 = 为什么选这条广告 ----

def test_explanation_states_why_this_ad() -> None:
    """REQ-ADS-AI-001：解释须说明"为什么选这条广告"（OQ-009 口径）。"""
    e = generate_explanation(judgment(), CANDS)
    assert e.ad_id == "ad_001"
    assert "ad_001" in e.text
    assert not e.degraded


def test_explanation_contrasts_with_other_candidates() -> None:
    """REQ-ADS-AI-001：口径要求对照"候选集中的其他广告"，故解释须提及其它候选。

    这是 OQ-009 定案带来的实质约束：解释必须能引用候选集作对照（只读），
    否则无法回答"为什么不是别的"。
    """
    e = generate_explanation(judgment(), CANDS)
    assert "ad_004" in e.text or "ad_008" in e.text
    assert "候选集" in e.text


def test_explanation_handles_single_candidate() -> None:
    """REQ-ADS-AI-001：候选集仅一条时，解释须说明"没有其他可选"，不得崩溃或缺句。"""
    e = generate_explanation(judgment(), CANDS[:1])
    assert "没有其他可选广告" in e.text


def test_explanation_handles_ad_id_absent_from_candidates() -> None:
    """REQ-ADS-AI-001：ad_id 不在候选集（不应发生，parser 已拦）时须保守处理，不抛异常。"""
    e = generate_explanation(judgment("ad_999"), CANDS)
    assert e.ad_id == "ad_999"
    assert e.text


# ---- INV-ADS-004：解释失败 ≠ 决策失败 ----

def test_explanation_degradation_keeps_ad_id() -> None:
    """INV-ADS-004（反例）：解释质量不达标时只降级解释，**ad_id 不变**。

    本测试同时断言一个**结构性**事实：`ExplanationVerdict` 不含 `ad_id` 字段 ——
    即校验函数在类型层面就无法改写决策。
    """
    e = Explanation(ad_id="ad_001", text="", degraded=False)  # 空解释 → too_short
    v = verify_explanation(e, BannedWords(["某词"]))
    assert v.degraded
    assert v.reason_code == "too_short"
    # 降级文本仍是安全的占位，且**Verdict 本身不携带 ad_id**（结构上无法改写决策）
    assert "不影响本次选择结果" in v.text
    assert not hasattr(v, "ad_id"), "ExplanationVerdict 不得携带 ad_id —— 解释路径无法改写决策"
    # 原始 Explanation 未被就地修改（只读）
    assert e.ad_id == "ad_001"


def test_explanation_with_banned_word_is_stripped(banned: BannedWords) -> None:
    """INV-ADS-004（反例）：解释含违禁词时必须被**剥离**，防止解释成为绕过合规 gate 的泄漏渠道。"""
    e = Explanation(ad_id="ad_001", text="这款产品包治百病，所以选它。", degraded=False)
    v = verify_explanation(e, banned)
    assert v.degraded
    assert v.reason_code == "banned_word"
    assert "包治百病" not in v.text, "违禁内容必须从解释文本中消失"


def test_verify_explanation_signature_cannot_rewrite_decision() -> None:
    """INV-ADS-004：`verify_explanation` 的签名**不含 ad_id** —— 结构上不可能改写决策。

    这是"解释路径隔离"的实现手段之二（见 explanation.py 模块 docstring）：
    不靠文档承诺，而靠调用方**没有把 ad_id 交给它**。
    """
    import inspect

    params = set(inspect.signature(verify_explanation).parameters)
    assert "ad_id" not in params
    assert params == {"explanation", "banned_words"}


def test_generate_explanation_does_not_mutate_judgment() -> None:
    """INV-ADS-004：generate_explanation 只读 —— 不得改变传入的 judgment。"""
    j = judgment()
    before = (j.ad_id, j.reason, j.confidence)
    generate_explanation(j, CANDS)
    assert (j.ad_id, j.reason, j.confidence) == before


def test_verify_explanation_ok_path(banned: BannedWords) -> None:
    """REQ-ADS-AI-001：正常解释必须通过校验（防止过度降级）。"""
    e = generate_explanation(judgment(), CANDS)
    v = verify_explanation(e, banned)
    assert isinstance(v, ExplanationVerdict)
    assert v.verdict == "ok"
    assert not v.degraded
    assert v.text == e.text


def test_verify_explanation_is_deterministic(banned: BannedWords) -> None:
    """REQ-ADS-ARCH-004：解释校验同为纯函数，同输入同输出。"""
    e = generate_explanation(judgment(), CANDS)
    assert all(verify_explanation(e, banned) == verify_explanation(e, banned) for _ in range(3))
