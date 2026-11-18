"""V3 合规内容分级的离线测试（PR-2）。

Verifies: REQ-ADS-NFR-SAFETY-008（内容并集判据）、REQ-ADS-NFR-SAFETY-009（年龄兜底）、
          REQ-ADS-NFR-SAFETY-010（三档分级）、REQ-ADS-ARCH-015（五步顺序不变）
Implements: ADR-006 D4

本模块包含多条**反例**（negative test）：CS2 / Among Us / R6S / Viscera 在各档位必须被拒；
并集判据的反例专挑「descriptors 为空、warnings 非空」的条目——只看 descriptors 会漏。
对应不变量：INV-V3-003（内容并集）、INV-V3-004（年龄兜底）、INV-V3-005（权威链顺序）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ads.banned_words import BannedWords
from compliance.content_rules import ContentPolicy, ContentRules, ContentRulesError
from compliance.pipeline import run_compliance
from compliance.models import ComplianceVerdict
from compliance.rules import SceneRules
from corpus import CorpusRepository, project_all
from scene.parser import parse_scene

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "data" / "scene-content-rules.yaml"

# 五条真实样本（id → 名称，便于阅读失败信息）
SAMPLES = {
    413150: "Stardew Valley",      # 无任何内容标记 → 三档全过
    730: "Counter-Strike 2",       # descriptors=[2,5] + Violence → 仅 competitive 过
    945360: "Among Us",            # descriptors=[]，warnings=[Violence, Blood] → 并集判据
    359550: "Rainbow Six Siege",   # age=17，warnings=[Violence] → 年龄兜底
    265210: "Viscera Cleanup",     # Gore/Blood → 三档全拒
}

SCENES = {
    "family": {"time_slot": "afternoon", "device": "tablet", "user_tags": ["family"]},
    "campus": {"time_slot": "afternoon", "device": "mobile", "user_tags": ["student"]},
    "competitive": {"time_slot": "evening", "device": "desktop", "user_tags": ["gamer"]},
}


@pytest.fixture(scope="module")
def rules():
    return ContentRules.load(RULES_PATH)


@pytest.fixture(scope="module")
def samples():
    corpus = CorpusRepository.load(ROOT / "data/corpus/items.jsonl", ROOT / "data/corpus/tags.jsonl")
    items = [corpus.get(i) for i in SAMPLES]
    assert all(item is not None for item in items), "五条样本必须在子集里（抽样规则保证）"
    return project_all(items)


@pytest.fixture(scope="module")
def env():
    return (
        BannedWords.load(ROOT / "data/banned_words.json"),
        SceneRules.load(ROOT / "data/scene_rules.json"),
    )


def _verdict(ad, ads, scene_raw, facts, rules, env):
    banned, scene_rules = env
    policy = ContentPolicy(rules=rules, facts={ad.ad_id: facts[ad.ad_id]})
    return run_compliance(ad, parse_scene(scene_raw), ads, banned, scene_rules, policy)


@pytest.mark.parametrize(
    "tier,expected",
    [
        ("family", {413150: True, 730: False, 945360: False, 359550: False, 265210: False}),
        ("campus", {413150: True, 730: False, 945360: False, 359550: False, 265210: False}),
        ("competitive", {413150: True, 730: True, 945360: True, 359550: True, 265210: False}),
    ],
)
def test_three_tier_matrix(tier, expected, samples, rules, env):
    """REQ-ADS-NFR-SAFETY-010：五条真实样本 × 三档场景，结果必须与预期矩阵一致。"""
    ads, facts = samples
    by_id = {ad.ad_id: ad for ad in ads}
    for item_id, should_pass in expected.items():
        ad = by_id[f"ad_{item_id}"]
        verdict = _verdict(ad, ads, SCENES[tier], facts, rules, env)
        assert verdict.approved is should_pass, (
            f"{SAMPLES[item_id]} 在 {tier} 档应为 {'通过' if should_pass else '拒绝'}，"
            f"实际 {'通过' if verdict.approved else verdict.detail_of('scene')}"
        )


def test_among_us_rejected_by_warnings_side(samples, rules, env):
    """REQ-ADS-NFR-SAFETY-008 / INV-V3-003：descriptors 为空但 warnings 含暴力 → 仍必须拒。

    这是"并集判据"的核心反例：只看 content_descriptors 的实现会把它放行。
    """
    ads, facts = samples
    ad = next(a for a in ads if a.ad_id == "ad_945360")
    assert facts[ad.ad_id].content_descriptors == (), "样本前提：descriptors 为空"
    verdict = _verdict(ad, ads, SCENES["family"], facts, rules, env)
    assert not verdict.approved
    assert verdict.rejected_rule() == "scene"
    assert "Violence" in (verdict.detail_of("scene") or "")


def test_age_gate_rejects_above_limit(samples, rules, env):
    """REQ-ADS-NFR-SAFETY-009 / INV-V3-004：required_age 超档位上限即拒。"""
    ads, facts = samples
    ad = next(a for a in ads if a.ad_id == "ad_359550")
    assert facts[ad.ad_id].required_age == 17
    # competitive 上限 18：年龄本身不拦（但内容仍按档位判定）
    assert 17 <= rules.tiers["competitive"].max_age
    # campus 上限 13：年龄超限
    assert 17 > rules.tiers["campus"].max_age
    detail = _verdict(ad, ads, SCENES["campus"], facts, rules, env).detail_of("scene") or ""
    assert "17" in detail


def test_pipeline_order_unchanged(samples, rules, env):
    """REQ-ADS-ARCH-015 / INV-V3-005：合规仍是五步且顺序固定，内容分级没有变成第六步。"""
    ads, facts = samples
    banned, scene_rules = env
    ad = ads[0]
    policy = ContentPolicy(rules=rules, facts={ad.ad_id: facts[ad.ad_id]})
    verdict = run_compliance(ad, parse_scene(SCENES["campus"]), ads, banned, scene_rules, policy)
    assert [r.rule for r in verdict.results] == [
        "output_exists", "banned_words", "banned_check", "category", "scene",
    ]


def test_policy_none_is_identical_to_v1(samples, rules, env):
    """REQ-ADS-ARCH-015：不传 policy 时行为与 V1 完全一致（新增能力是纯增量）。"""
    ads, _facts = samples
    banned, scene_rules = env
    scene = parse_scene(SCENES["campus"])
    with_policy_off = run_compliance(ads[0], scene, ads, banned, scene_rules)
    explicit_none = run_compliance(ads[0], scene, ads, banned, scene_rules, None)
    assert isinstance(with_policy_off, ComplianceVerdict)
    assert with_policy_off == explicit_none


def test_content_rules_fail_closed():
    """REQ-ADS-NFR-SAFETY-010：规则文件缺失或非法即拒绝启动（fail-closed）。"""
    with pytest.raises(ContentRulesError):
        ContentRules.load(ROOT / "data" / "no-such-rules.yaml")


def test_content_rules_reject_unknown_tier_reference(tmp_path=None):
    """REQ-ADS-NFR-SAFETY-010：tag_to_tier 指向未知档位必须拒绝。"""
    import io
    import tempfile

    payload = (
        "tiers:\n  campus:\n    max_age: 13\n    block_labels: [Violence]\n"
        "default_tier: campus\ntag_to_tier:\n  gamer: nope\ndescriptor_labels: {}\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
        handle.write(payload)
        path = Path(handle.name)
    try:
        with pytest.raises(ContentRulesError):
            ContentRules.load(path)
    finally:
        path.unlink(missing_ok=True)
