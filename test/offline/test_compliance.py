"""compliance 合规过滤模块离线测试（REQ-006~009）。

每个 Invariant 都包含"必须失败"的反例测试（课程 D4 要求）。
运行：仓库根目录下 pytest test/offline/test_compliance.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ads.banned_words import BannedWords
from ads.models import Ad
from ads.repository import AdRepository
from compliance.pipeline import (
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


# ---- REQ-004/005 output 存在性 ----

def test_check_output_reject_not_in_candidates(repo: AdRepository) -> None:
    r = check_output(repo.get("ad_001"), candidates_of(repo, "ad_002", "ad_004"))
    assert not r.ok
    assert "不在候选集" in r.detail


def test_check_output_ok_in_candidates(repo: AdRepository) -> None:
    r = check_output(repo.get("ad_001"), candidates_of(repo, "ad_001"))
    assert r.ok


# ---- REQ-008 违禁词（反例测试） ----

def test_check_banned_words_reject(repo: AdRepository, banned: BannedWords) -> None:
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


# ---- REQ-007 敏感品类（反例测试） ----

def test_check_category_reject_financial(repo: AdRepository, rules: SceneRules) -> None:
    r = check_category(repo.get("ad_007"), rules)  # financial_guarantee
    assert not r.ok
    assert "黑名单" in r.detail


def test_check_category_reject_adult(repo: AdRepository, rules: SceneRules) -> None:
    assert not check_category(repo.get("ad_006"), rules).ok


# ---- REQ-009 场景硬约束（反例测试） ----

def test_check_scene_night_gaming(repo: AdRepository, rules: SceneRules) -> None:
    r = check_scene(repo.get("ad_003"), Scene("night", "mobile"), rules)
    assert not r.ok
    assert "夜间禁展示" in r.detail


def test_check_scene_campus_adult(repo: AdRepository, rules: SceneRules) -> None:
    r = check_scene(repo.get("ad_006"), Scene("afternoon", "mobile", ["student"]), rules)
    assert not r.ok
    assert "校园" in r.detail


def test_check_scene_device_mismatch(repo: AdRepository, rules: SceneRules) -> None:
    r = check_scene(repo.get("ad_003"), Scene("afternoon", "tablet"), rules)
    assert not r.ok
    assert "设备" in r.detail


def test_check_scene_ok_normal(repo: AdRepository, rules: SceneRules) -> None:
    r = check_scene(repo.get("ad_001"), Scene("night", "mobile"), rules)
    assert r.ok


# ---- REQ-006 管道：正常通过 / 任一失败即 REJECT ----

def test_run_compliance_approve_normal_ad(repo, banned: BannedWords, rules: SceneRules) -> None:
    scene = Scene("night", "mobile", ["student"])
    candidates = repo.filter_by_scene(scene)
    v = run_compliance(repo.get("ad_001"), scene, candidates, banned, rules)
    assert v.approved
    assert v.rejected_rule() is None


def test_run_compliance_reject_financial_category(repo, banned: BannedWords, rules: SceneRules) -> None:
    scene = Scene("afternoon", "mobile")
    candidates = repo.all()  # 预筛未过滤品类，compliance 必须兜住
    v = run_compliance(repo.get("ad_007"), scene, candidates, banned, rules)
    assert not v.approved
    assert v.rejected_rule() == "category"


def test_run_compliance_reject_output_mismatch(repo, banned: BannedWords, rules: SceneRules) -> None:
    scene = Scene("afternoon", "mobile")
    v = run_compliance(repo.get("ad_001"), scene, candidates_of(repo, "ad_002"), banned, rules)
    assert not v.approved
    assert v.rejected_rule() == "output_exists"
