"""违禁词表回归测试（独立于 test_ads.py，专项锁住两个已修缺陷）。

Verifies: REQ-ADS-NFR-SAFETY-003（违禁词命中即 REJECT）、REQ-ADS-ARCH-004（确定性可复现）、
          INV-ADS-007（含违禁词的广告绝不被展示）。
覆盖缺陷：BUG-006（等长命中非确定性）、BUG-007（load fail-closed 不一致）。

设计说明（V4 / 沙箱兼容）：不使用 tmp_path，在文件 I/O 边界打桩。
运行：仓库根目录下 pytest test/offline/test_banned_words.py
"""

from __future__ import annotations

import builtins
import io
import json
from pathlib import Path

import pytest

from ads.banned_words import BannedWords, BannedWordsLoadError
from ads.models import Ad
from ads.repository import AdRepository
from compliance.pipeline import check_banned_words

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


@pytest.fixture
def banned() -> BannedWords:
    return BannedWords.load(DATA_DIR / "banned_words.json")


@pytest.fixture
def repo() -> AdRepository:
    return AdRepository.load(DATA_DIR / "ads.json")


class _FakePath:
    """在 p.exists() 边界打桩，不触碰磁盘。"""

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
    monkeypatch.setattr(builtins, "open", lambda *a, **k: io.StringIO(text))


# ===========================================================================
# BUG-006 回归：等长命中必须确定性（与词表顺序无关）
# ===========================================================================

def test_equal_length_hits_are_order_independent() -> None:
    """REQ-ADS-ARCH-004 / BUG-006：同一文本在不同词表顺序下必须给出同一命中。

    修复前：max(hits, key=len) 在等长时取词表中最先出现者 → 顺序敏感。
    修复后：max(hits, key=lambda w: (len(w), w)) → 最长优先，同长按字典序。
    """
    words = ["赌博", "博彩", "赌场", "返现"]  # 全部等长（2 字）
    text = "赌博博彩赌场返现"
    forward = BannedWords(list(words)).check(text)
    backward = BannedWords(list(reversed(words))).check(text)
    assert forward == backward, f"命中随词表顺序变化: {forward!r} vs {backward!r}"


def test_equal_length_hit_is_codepoint_smallest() -> None:
    """长度相同时取 **Unicode 码点最小**者——这是明确规则，不是实现细节。

    注意：这是**码点序**，不是中文拼音序或笔画序。对中文而言两者不同：
        博 U+535A  <  赌 U+8D4C  <  返 U+8FD4
    选用码点序的理由：它完全确定（同输入同输出），不依赖任何语言环境或排序规则，
    因此满足 REQ-ADS-ARCH-004 的"逐位一致"。审计时请以码点序为准。
    """
    words = ["返现", "赌博", "博彩"]
    assert BannedWords(words).check("赌博博彩返现") == "博彩"  # 码点最小
    # 码点序证据（不是拼音序：拼音是 bo < du < fan，恰好一致，但 博<赌<返 是码点序）
    assert ord("博") < ord("赌") < ord("返")


def test_tiebreak_is_independent_of_wordlist_order() -> None:
    """等长命中在任意词表排列下都必须稳定——这是确定性要求的操作性检验。"""
    import itertools

    words = ["返现", "赌博", "博彩", "刷单"]
    text = "赌博博彩返现刷单"
    results = {BannedWords(list(p)).check(text) for p in itertools.permutations(words)}
    assert len(results) == 1, f"同一文本在 24 种词表排列下产生多个结果: {results}"


def test_longest_wins_over_shorter() -> None:
    """最长优先：'兼职刷单'(4) 必须胜过 '刷单'(2)。"""
    assert BannedWords(["刷单", "兼职刷单"]).check("兼职刷单日赚500") == "兼职刷单"
    assert BannedWords(["兼职刷单", "刷单"]).check("兼职刷单日赚500") == "兼职刷单"


def test_real_wordlist_is_deterministic_under_reversal(banned: BannedWords) -> None:
    """用真实词表验证：整体逆序不得改变任何素材文本的命中结果。"""
    reversed_words = BannedWords(list(reversed(banned.words)))
    probes = [
        "赌博博彩赌场网贷刷单稳赚保本根治代孕捐卵色情催收日赚暴利返现",
        "高利贷特效药百分百无风险零投入内部价",
        "兼职刷单包治百病祖传秘方",
        "加班夜，一杯热美式送到家",
        "零基础三个月入门大模型开发",
    ]
    for t in probes:
        assert banned.check(t) == reversed_words.check(t), f"文本 {t!r} 的命中随词表顺序变化"


# ===========================================================================
# BUG-007 回归：load 必须 fail-closed 且错误类型一致
# ===========================================================================

def test_load_missing_file_rejected() -> None:
    """BUG-007：文件不存在必须以专属错误拒绝（原先抛 FileNotFoundError）。"""
    missing = _FakePath(DATA_DIR / "___nope___.json", exists=False)
    with pytest.raises(BannedWordsLoadError):
        BannedWords.load(missing)


def test_load_invalid_json_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUG-007：非法 JSON 必须以专属错误拒绝（原先抛原始 JSONDecodeError）。"""
    _fake_read(monkeypatch, "not json{")
    with pytest.raises(BannedWordsLoadError):
        BannedWords.load(_FakePath(DATA_DIR / "banned_words.json"))


def test_load_top_level_not_list_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUG-007：顶层非数组必须拒绝。"""
    _fake_read(monkeypatch, json.dumps({"words": ["赌博"]}))
    with pytest.raises(BannedWordsLoadError):
        BannedWords.load(_FakePath(DATA_DIR / "banned_words.json"))


def test_load_non_string_element_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUG-007：元素非字符串必须拒绝。"""
    _fake_read(monkeypatch, json.dumps(["赌博", 123]))
    with pytest.raises((BannedWordsLoadError, TypeError)):
        BannedWords.load(_FakePath(DATA_DIR / "banned_words.json"))


def test_load_empty_list_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """空词表 = 合规过滤形同虚设 → 必须拒绝启动（fail-closed）。"""
    _fake_read(monkeypatch, json.dumps([]))
    with pytest.raises(BannedWordsLoadError, match="空"):
        BannedWords.load(_FakePath(DATA_DIR / "banned_words.json"))


def test_load_ok_returns_wordlist(banned: BannedWords) -> None:
    """正向：真实词表可加载且非空。"""
    assert len(banned.words) == 24
    assert all(w == w.strip().lower() for w in banned.words)
    assert len(set(banned.words)) == len(banned.words)  # 无重复


# ===========================================================================
# 全覆盖回归：24 个违禁词每一个都必须真的能被 gate 拦下
# ===========================================================================

def test_every_banned_word_is_actually_blocked(banned: BannedWords) -> None:
    """REQ-ADS-NFR-SAFETY-003 / INV-ADS-007：词表中**每一个**词都必须真的拦得住。

    这是"违禁词拦截"这个安全主张的直接证据——此前 24 个词全部没有真实数据验证。
    """
    assert len(banned.words) == 24, "词表规模变化时本测试需同步更新"
    for word in banned.words:
        ad = Ad.from_dict(
            {
                "ad_id": "ad_900",
                "title": f"推广：{word}",
                "copy": "正常文案",
                "category": "retail",
                "target_tags": [],
                "scene_restrictions": {
                    "not_night": False,
                    "not_campus": False,
                    "allowed_devices": ["mobile"],
                },
                "banned_check": "checked",
            }
        )
        result = check_banned_words(ad, banned)
        assert not result.ok, f"违禁词 {word!r} 出现在 title 却未被拦截"
        assert word in result.detail or "命中违禁词" in result.detail


def test_banned_word_in_copy_is_blocked(banned: BannedWords) -> None:
    """违禁词出现在 copy（而非 title）时同样必须拦截——check_all 覆盖两处。"""
    ad = Ad.from_dict(
        {
            "ad_id": "ad_901",
            "title": "正常标题",
            "copy": "本产品包治百病",
            "category": "retail",
            "target_tags": [],
            "scene_restrictions": {"not_night": False, "not_campus": False, "allowed_devices": ["mobile"]},
            "banned_check": "checked",
        }
    )
    assert not check_banned_words(ad, banned).ok


def test_clean_ads_are_not_falsely_blocked(repo: AdRepository, banned: BannedWords) -> None:
    """对照样本：真实素材**不得**被违禁词 gate 误拦（防止过度拦截）。"""
    for ad in repo.all():
        assert check_banned_words(ad, banned).ok, f"{ad.ad_id} 被违禁词 gate 误拦"
