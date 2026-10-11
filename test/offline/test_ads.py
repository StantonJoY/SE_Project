"""ads 素材库模块离线测试。

Verifies: REQ-ADS-FR-001（素材加载）、REQ-ADS-ARCH-001（schema 整批 fail-closed）、
          REQ-ADS-NFR-SAFETY-003（违禁词）、INV-ADS-015（素材契约）。
运行：仓库根目录下 pytest test/offline/test_ads.py

设计说明（结构性约束 V4 / 沙箱兼容）：本模块**不使用 tmp_path**，
而是在文件 I/O 边界打桩（`p.exists` / `builtins.open`），因此不依赖磁盘临时目录。
"""

from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest

from ads.banned_words import BannedWords
from ads.repository import AdLoadError, AdRepository
from scene.models import Scene

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

REAL_ADS_PATH = DATA_DIR / "ads.json"


class _FakePath:
    """在 `p.exists()` 边界打桩：路径"存在"与否由测试决定，永不触碰磁盘。"""

    def __init__(self, target: Path, *, exists: bool = True) -> None:
        self._target = target
        self._exists = exists

    def exists(self) -> bool:
        return self._exists

    def __fspath__(self) -> str:
        return str(self._target)

    def __str__(self) -> str:
        return str(self._target)


def _fake_read(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """让 `open()` 返回内存中的文本，避免写任何临时文件。"""
    import io

    def fake_open(*args, **kwargs):
        return io.StringIO(text)

    monkeypatch.setattr(builtins, "open", fake_open)


def valid_ad(ad_id: str = "ad_900") -> dict:
    """构造一条字段完整合法的素材（供变异测试用）。"""
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


# ---- REQ-ADS-FR-001 加载 ----

def test_load_ok(repo: AdRepository) -> None:
    """REQ-ADS-FR-001：加载条数 = 数据文件条数。

    断言以**相对量**表达（自行读取文件比对），不写死具体条数——
    素材库会随 OQ-003 扩充，写死会导致无故失败（见 BUG-005）。
    """
    raw = json.loads(REAL_ADS_PATH.read_text(encoding="utf-8"))
    assert repo.count == len(raw)
    assert repo.get("ad_001") is not None


def test_every_rule_category_has_material(repo: AdRepository) -> None:
    """REQ-ADS-NFR-SAFETY-002/004：规则引用的每个品类都必须有素材，否则规则永久空转。

    本测试使「死规则」无法再次静默引入（AF-001 的回归防线）。
    """
    from compliance.rules import SceneRules

    rules = SceneRules.load(DATA_DIR / "scene_rules.json")
    categories = {a.category for a in repo.all()}
    for rule_name in (
        "category_blacklist",
        "night_blocked_categories",
        "campus_blocked_categories",
    ):
        for value in getattr(rules, rule_name):
            assert value in categories, (
                f"规则 {rule_name} 含 {value!r}，但素材库无该品类 → 该规则永远无法被触发"
            )


def test_load_missing_file_rejected() -> None:
    """REQ-ADS-ARCH-001 / INV-ADS-015（反例）：文件不存在必须拒绝，不静默返回空库。"""
    missing = _FakePath(DATA_DIR / "definitely_not_here.json", exists=False)
    with pytest.raises(AdLoadError):
        AdRepository.load(missing)


def test_load_invalid_json_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-ADS-ARCH-001 / INV-ADS-015（反例）：非法 JSON 必须拒绝。"""
    _fake_read(monkeypatch, "not json{")
    with pytest.raises(AdLoadError):
        AdRepository.load(_FakePath(REAL_ADS_PATH))


def test_load_top_level_not_list_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-ADS-ARCH-001 / INV-ADS-015（反例）：顶层非数组必须拒绝。"""
    _fake_read(monkeypatch, json.dumps({"ad_id": "ad_900"}))
    with pytest.raises(AdLoadError):
        AdRepository.load(_FakePath(REAL_ADS_PATH))


def test_load_duplicate_ad_id_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-ADS-FR-001 / INV-ADS-015（反例）：重复 ad_id 必须报错并终止加载。"""
    items = [valid_ad("ad_900"), valid_ad("ad_900")]
    _fake_read(monkeypatch, json.dumps(items, ensure_ascii=False))
    with pytest.raises(AdLoadError, match="ad_id 重复"):
        AdRepository.load(_FakePath(REAL_ADS_PATH))


# ---- REQ-ADS-ARCH-001 schema 整批 fail-closed ----

def test_load_missing_required_field_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-ADS-ARCH-001 / INV-ADS-015（反例）：缺必填字段必须拒绝整批。"""
    bad = valid_ad()
    del bad["copy"]
    _fake_read(monkeypatch, json.dumps([bad], ensure_ascii=False))
    with pytest.raises(AdLoadError, match="不合法"):
        AdRepository.load(_FakePath(REAL_ADS_PATH))


def test_load_invalid_device_value_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-ADS-ARCH-001 / INV-ADS-015（反例）：非法设备枚举必须被 schema 拦下。"""
    bad = valid_ad()
    bad["scene_restrictions"]["allowed_devices"] = ["pc"]  # 非法枚举
    _fake_read(monkeypatch, json.dumps([bad], ensure_ascii=False))
    with pytest.raises(AdLoadError, match="不合法"):
        AdRepository.load(_FakePath(REAL_ADS_PATH))


def test_load_one_bad_among_good_fails_whole_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-ADS-ARCH-001 / INV-ADS-015：整批 fail-closed——不跳过坏条目、不部分加载。"""
    bad = valid_ad("ad_901")
    del bad["category"]
    items = [valid_ad("ad_900"), bad]
    _fake_read(monkeypatch, json.dumps(items, ensure_ascii=False))
    with pytest.raises(AdLoadError, match="不合法"):
        AdRepository.load(_FakePath(REAL_ADS_PATH))


# ---- 查询 ----

def test_get_found(repo: AdRepository) -> None:
    """REQ-ADS-FR-001：按 ad_id 查询命中。"""
    ad = repo.get("ad_001")
    assert ad is not None
    assert ad.category == "food_delivery"


def test_get_missing_returns_none(repo: AdRepository) -> None:
    """REQ-ADS-FR-001：查询不存在的 ad_id 返回 None（不抛错）。"""
    assert repo.get("ad_999") is None


# ---- REQ-ADS-NFR-SAFETY-004 / INV-ADS-008 场景预筛（规则预筛前置） ----

def test_filter_night_excludes_not_night(repo: AdRepository) -> None:
    """INV-ADS-008：声明 not_night 的广告不得进入夜间候选集。"""
    ids = {a.ad_id for a in repo.filter_by_scene(Scene(time_slot="night", device="mobile"))}
    assert "ad_002" not in ids  # not_night=true
    assert "ad_001" in ids      # 夜间可推


def test_filter_campus_excludes_adult(repo: AdRepository) -> None:
    """INV-ADS-008：声明 not_campus 的广告不得进入校园候选集。"""
    ids = {a.ad_id for a in repo.filter_by_scene(Scene(time_slot="afternoon", device="mobile", user_tags=("student",)))}
    assert "ad_006" not in ids  # not_campus=true（成人品类校园禁）
    assert "ad_005" in ids


def test_filter_device_excludes_unsupported(repo: AdRepository) -> None:
    """INV-ADS-008：设备不在允许列表的广告不得进入候选集。"""
    ids = {a.ad_id for a in repo.filter_by_scene(Scene(time_slot="afternoon", device="tablet"))}
    assert "ad_003" not in ids  # 仅 mobile
    assert "ad_008" not in ids  # 仅 mobile/desktop
    assert "ad_004" in ids      # 全设备


# ---- REQ-ADS-NFR-SAFETY-003 违禁词 ----

def test_banned_words_hit(banned: BannedWords) -> None:
    """REQ-ADS-NFR-SAFETY-003：命中违禁词时返回最长命中词。"""
    assert banned.check("兼职刷单日赚500") == "兼职刷单"
    assert banned.check("这款药包治百病") == "包治百病"


def test_banned_words_miss(banned: BannedWords) -> None:
    """REQ-ADS-NFR-SAFETY-003：正常文案不得误报。"""
    assert banned.check("加班夜，一杯热美式送到家") is None


def test_banned_words_check_all(banned: BannedWords) -> None:
    """REQ-ADS-NFR-SAFETY-003：对 title + copy 全量检查。"""
    assert banned.check_all("正常文案", "稳赚不赔") == "稳赚"
    assert banned.check_all("正常文案", "另一条正常") is None
