"""scene 场景模块离线测试（REQ-003）。

运行：仓库根目录下 pytest test/offline/test_scene.py
"""

from __future__ import annotations

import pytest

from scene.models import Scene
from scene.parser import SceneInputError, parse_scene


def test_parse_ok_full() -> None:
    s = parse_scene(
        {"time_slot": "night", "device": "mobile", "user_tags": ["student", "student", "gamer"]}
    )
    assert s.time_slot == "night"
    assert s.device == "mobile"
    assert s.user_tags == ("student", "gamer")  # 去重保序


def test_parse_ok_without_tags() -> None:
    s = parse_scene({"time_slot": "morning", "device": "desktop"})
    assert s.user_tags == ()


def test_parse_reject_missing_field() -> None:
    with pytest.raises(SceneInputError, match="不合法"):
        parse_scene({"time_slot": "night"})


def test_parse_reject_invalid_time_slot() -> None:
    with pytest.raises(SceneInputError):
        parse_scene({"time_slot": "midnight", "device": "mobile"})


def test_parse_reject_invalid_device() -> None:
    with pytest.raises(SceneInputError):
        parse_scene({"time_slot": "night", "device": "pc"})


def test_parse_reject_non_dict() -> None:
    with pytest.raises(SceneInputError, match="JSON 对象"):
        parse_scene("night")


def test_parse_reject_extra_field() -> None:
    with pytest.raises(SceneInputError):
        parse_scene({"time_slot": "night", "device": "mobile", "location": "hk"})


def test_parse_reject_bad_tags_type() -> None:
    with pytest.raises(SceneInputError):
        parse_scene({"time_slot": "night", "device": "mobile", "user_tags": "student"})
