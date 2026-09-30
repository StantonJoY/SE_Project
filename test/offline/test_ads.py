"""ads 素材库模块离线测试（REQ-001/002/008）。

运行：仓库根目录下 pytest test/offline/test_ads.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ads.banned_words import BannedWords
from ads.repository import AdLoadError, AdRepository

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


class FakeScene:
    """场景桩（duck-typing；P3 换正式 scene 模块）。"""

    def __init__(self, time_slot: str = "afternoon", device: str = "mobile", user_tags: list[str] | None = None):
        self.time_slot = time_slot
        self.device = device
        self.user_tags = user_tags or []


def valid_ad(ad_id: str = "ad_900") -> dict:
    return {
        "ad_id": ad_id,
        "title": "测试广告",
        "copy": "测试文案",
        "category": "retail",
        "target_tags": ["student"],
        "scene_restrictions": {
            "not_night": False,
            "not_campus": False,
            "allowed_devices": ["mobile", "desktop", "tablet"],
        },
        "banned_check": "pending",
    }


@pytest.fixture
def repo() -> AdRepository:
    return AdRepository.load(DATA_DIR / "ads.json")


@pytest.fixture
def banned() -> BannedWords:
    return BannedWords.load(DATA_DIR / "banned_words.json")


# ---- REQ-001 加载 ----

def test_load_ok(repo: AdRepository) -> None:
    assert repo.count == 8
    assert repo.get("ad_001") is not None


def test_load_missing_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(AdLoadError):
        AdRepository.load(tmp_path / "nope.json")


def test_load_invalid_json_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json{", encoding="utf-8")
    with pytest.raises(AdLoadError):
        AdRepository.load(p)


def test_load_duplicate_ad_id_rejected(tmp_path: Path) -> None:
    items = [valid_ad("ad_900"), valid_ad("ad_900")]
    p = tmp_path / "dup.json"
    p.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AdLoadError, match="ad_id 重复"):
        AdRepository.load(p)


# ---- REQ-002 字段完整合法 ----

def test_load_missing_required_field_rejected(tmp_path: Path) -> None:
    bad = valid_ad()
    del bad["copy"]
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([bad], ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AdLoadError, match="不合法"):
        AdRepository.load(p)


def test_load_invalid_device_value_rejected(tmp_path: Path) -> None:
    bad = valid_ad()
    bad["scene_restrictions"]["allowed_devices"] = ["pc"]  # 非法枚举
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([bad], ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AdLoadError, match="不合法"):
        AdRepository.load(p)


# ---- 查询 ----

def test_get_found(repo: AdRepository) -> None:
    ad = repo.get("ad_001")
    assert ad is not None
    assert ad.category == "food_delivery"


def test_get_missing_returns_none(repo: AdRepository) -> None:
    assert repo.get("ad_999") is None


# ---- 场景预筛（规则预筛前置，REQ-009 数据来源） ----

def test_filter_night_excludes_not_night(repo: AdRepository) -> None:
    ids = {a.ad_id for a in repo.filter_by_scene(FakeScene(time_slot="night"))}
    assert "ad_002" not in ids  # not_night=true
    assert "ad_001" in ids      # 夜间可推


def test_filter_campus_excludes_adult(repo: AdRepository) -> None:
    ids = {a.ad_id for a in repo.filter_by_scene(FakeScene(user_tags=["student"]))}
    assert "ad_006" not in ids  # not_campus=true（成人品类校园禁）
    assert "ad_005" in ids


def test_filter_device_excludes_unsupported(repo: AdRepository) -> None:
    ids = {a.ad_id for a in repo.filter_by_scene(FakeScene(device="tablet"))}
    assert "ad_003" not in ids  # 仅 mobile
    assert "ad_008" not in ids  # 仅 mobile/desktop
    assert "ad_004" in ids      # 全设备


# ---- REQ-008 违禁词 ----

def test_banned_words_hit(banned: BannedWords) -> None:
    assert banned.check("兼职刷单日赚500") == "兼职刷单"
    assert banned.check("这款药包治百病") == "包治百病"


def test_banned_words_miss(banned: BannedWords) -> None:
    assert banned.check("加班夜，一杯热美式送到家") is None


def test_banned_words_check_all(banned: BannedWords) -> None:
    assert banned.check_all("正常文案", "稳赚不赔") == "稳赚"
    assert banned.check_all("正常文案", "另一条正常") is None
