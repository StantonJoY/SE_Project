"""compliance 合规过滤模块离线测试。

Verifies: REQ-ADS-NFR-SAFETY-001（零逃逸）、REQ-ADS-NFR-SAFETY-002（敏感品类）、
          REQ-ADS-NFR-SAFETY-003（违禁词）、REQ-ADS-NFR-SAFETY-004（场景约束）、
          REQ-ADS-ARCH-001（banned_check 状态 fail-closed）、REQ-ADS-ARCH-002（闭集选择）、
          REQ-ADS-ARCH-004（确定性可复现：纯函数 + 无全局状态）、
          INV-ADS-001（合规强制）、INV-ADS-002（集外拒绝）、
          INV-ADS-007（品类与违禁词）、INV-ADS-008（场景双层）、INV-ADS-013（失败不崩溃）。
每个 Invariant 都包含"必须失败"的反例测试（课程 D4 / 结构性约束 V2）。
运行：仓库根目录下 pytest test/offline/test_compliance.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ads.banned_words import BannedWords
from ads.models import Ad
from ads.repository import AdRepository
from compliance.pipeline import (
    check_banned_check,
    check_banned_words,
    check_category,
    check_output,
    check_scene,
    run_compliance,
)
from compliance.rules import SceneRules
from scene.models import Scene

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


@pytest.fixture
def repo() -> AdRepository:
    return AdRepository.load(DATA_DIR / "ads.json")


@pytest.fixture
def banned() -> BannedWords:
    return BannedWords.load(DATA_DIR / "banned_words.json")


@pytest.fixture
def rules() -> SceneRules:
    return SceneRules.load(DATA_DIR / "scene_rules.json")


def candidates_of(repo: AdRepository, *ids: str) -> list[Ad]:
    return [a for a in repo.all() if a.ad_id in ids]


# ---- REQ-ADS-ARCH-002 / INV-ADS-002：候选集存在性 ----

def test_check_output_reject_not_in_candidates(repo: AdRepository) -> None:
    """INV-ADS-002（反例）：LLM 输出候选集外的 ad_id 必须被拒绝。"""
    r = check_output(repo.get("ad_001"), candidates_of(repo, "ad_002", "ad_004"))
    assert not r.ok
    assert "不在候选集" in r.detail


def test_check_output_ok_in_candidates(repo: AdRepository) -> None:
    """REQ-ADS-ARCH-002：候选集内的 ad_id 必须通过。"""
    r = check_output(repo.get("ad_001"), candidates_of(repo, "ad_001"))
    assert r.ok


# ---- REQ-ADS-ARCH-001 / INV-ADS-001：banned_check 状态（fail-closed） ----

def test_check_banned_check_rejects_banned(repo: AdRepository) -> None:
    """INV-ADS-001（反例）：标为 `banned` 的素材必须被拦截（AF-004 的回归防线）。

    本条正是"声明了却不强制"的修复验证——此前 `banned_check: "banned"` 仍会被展示。
    """
    ad = repo.get("ad_014")
    assert ad is not None and ad.banned_check == "banned", "夹具失效：ad_014 应为 banned"
    r = check_banned_check(ad)
    assert not r.ok
    assert "banned" in r.detail


def test_check_banned_check_rejects_pending(repo: AdRepository) -> None:
    """INV-ADS-001（反例）：未核验（`pending`）的素材必须 fail-closed 拒绝。"""
    ad = repo.get("ad_013")
    assert ad is not None and ad.banned_check == "pending", "夹具失效：ad_013 应为 pending"
    r = check_banned_check(ad)
    assert not r.ok
    assert "pending" in r.detail


def test_check_banned_check_accepts_checked(repo: AdRepository) -> None:
    """正向：只有显式 `checked` 放行。"""
    ad = repo.get("ad_001")
    assert ad is not None and ad.banned_check == "checked"
    assert check_banned_check(ad).ok


def test_run_compliance_rejects_banned_status(repo, banned: BannedWords, rules: SceneRules) -> None:
    """INV-ADS-001：管道必须把 `banned` 素材整条拒掉（不是只在单检查里拒）。"""
    scene = Scene("afternoon", "mobile", ["student"])
    v = run_compliance(repo.get("ad_014"), scene, repo.all(), banned, rules)
    assert not v.approved
    assert v.rejected_rule() == "banned_check"


def test_pipeline_order_puts_banned_check_before_category(repo, banned: BannedWords, rules: SceneRules) -> None:
    """管道顺序契约：output_exists → banned_words → banned_check → category → scene。

    用一条**同时**违反 banned_check 与 category 的构造广告验证顺序：
    先报出的失败规则必须是 banned_check（更靠前）。
    """
    ad = Ad.from_dict(
        {
            "ad_id": "ad_910",
            "title": "正常标题",
            "copy": "正常文案",
            "category": "medical",  # 违反 category
            "target_tags": [],
            "scene_restrictions": {"not_night": False, "not_campus": False, "allowed_devices": ["mobile"]},
            "banned_check": "banned",  # 同时违反 banned_check
        }
    )
    scene = Scene("afternoon", "mobile")
    v = run_compliance(ad, scene, [ad], banned, rules)
    assert not v.approved
    assert v.rejected_rule() == "banned_check", "管道顺序漂移：banned_check 应排在 category 之前"


# ---- REQ-ADS-NFR-SAFETY-003 / INV-ADS-007：违禁词（反例测试） ----

def test_check_banned_words_reject(repo: AdRepository, banned: BannedWords) -> None:
    """INV-ADS-007（反例）：含违禁词的广告必须 REJECT。"""
    ad = Ad.from_dict(
        {
            "ad_id": "ad_bad",
            "title": "稳赚不赔理财计划",
            "copy": "保本高收益，无风险",
            "category": "finance",
            "target_tags": ["office_worker"],
            "scene_restrictions": {"not_night": False, "not_campus": False, "allowed_devices": ["mobile"]},
            "banned_check": "pending",
        }
    )
    r = check_banned_words(ad, banned)
    assert not r.ok
    assert "命中违禁词" in r.detail


# ---- REQ-ADS-NFR-SAFETY-002 / INV-ADS-007：敏感品类（反例测试） ----

def test_check_category_reject_financial(repo: AdRepository, rules: SceneRules) -> None:
    """INV-ADS-007（反例）：金融承诺品类必须 REJECT。"""
    r = check_category(repo.get("ad_007"), rules)  # financial_guarantee
    assert not r.ok
    assert "黑名单" in r.detail


def test_check_category_reject_adult(repo: AdRepository, rules: SceneRules) -> None:
    """INV-ADS-007（反例）：成人品类必须 REJECT。"""
    assert not check_category(repo.get("ad_006"), rules).ok


# ---- REQ-ADS-NFR-SAFETY-004 / INV-ADS-008：场景硬约束（反例测试） ----

def test_check_scene_night_gaming(repo: AdRepository, rules: SceneRules) -> None:
    """INV-ADS-008（反例）：规则级夜间禁 gaming 品类必须 REJECT。"""
    r = check_scene(repo.get("ad_003"), Scene("night", "mobile"), rules)
    assert not r.ok
    assert "夜间禁展示" in r.detail


def test_check_scene_campus_adult(repo: AdRepository, rules: SceneRules) -> None:
    """INV-ADS-008（反例）：规则级校园禁 adult 品类必须 REJECT。"""
    r = check_scene(repo.get("ad_006"), Scene("afternoon", "mobile", ["student"]), rules)
    assert not r.ok
    assert "校园" in r.detail


def test_check_scene_device_mismatch(repo: AdRepository, rules: SceneRules) -> None:
    """INV-ADS-008（反例）：素材声明的设备白名单不符必须 REJECT。"""
    r = check_scene(repo.get("ad_003"), Scene("afternoon", "tablet"), rules)
    assert not r.ok
    assert "设备" in r.detail


def test_check_scene_ok_normal(repo: AdRepository, rules: SceneRules) -> None:
    """REQ-ADS-NFR-SAFETY-004：正常场景下合规广告必须通过。"""
    r = check_scene(repo.get("ad_001"), Scene("night", "mobile"), rules)
    assert r.ok


# ---- REQ-ADS-NFR-SAFETY-001 / INV-ADS-001：管道——正常通过 / 任一失败即 REJECT ----

def test_run_compliance_approve_normal_ad(repo, banned: BannedWords, rules: SceneRules) -> None:
    """INV-ADS-001：五步全通过 → APPROVE。"""
    scene = Scene("night", "mobile", ["student"])
    candidates = repo.filter_by_scene(scene)
    v = run_compliance(repo.get("ad_001"), scene, candidates, banned, rules)
    assert v.approved
    assert v.rejected_rule() is None


def test_run_compliance_reject_financial_category(repo, banned: BannedWords, rules: SceneRules) -> None:
    """INV-ADS-001：品类 gate 在管道内兜住（即使预筛未过滤品类）。"""
    scene = Scene("afternoon", "mobile")
    candidates = repo.all()  # 预筛未过滤品类，compliance 必须兜住
    v = run_compliance(repo.get("ad_007"), scene, candidates, banned, rules)
    assert not v.approved
    assert v.rejected_rule() == "category"


def test_run_compliance_reject_output_mismatch(repo, banned: BannedWords, rules: SceneRules) -> None:
    """INV-ADS-001 / INV-ADS-002：管道第一步 output_exists 拦截集外输出。"""
    scene = Scene("afternoon", "mobile")
    v = run_compliance(repo.get("ad_001"), scene, candidates_of(repo, "ad_002"), banned, rules)
    assert not v.approved
    assert v.rejected_rule() == "output_exists"
