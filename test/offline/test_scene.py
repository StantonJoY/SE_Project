"""scene 场景模块离线测试。

Verifies: REQ-ADS-FR-002（场景输入校验后方可进入流程）。
运行：仓库根目录下 pytest test/offline/test_scene.py
"""

from __future__ import annotations

import pytest

from scene.parser import SceneInputError, parse_scene


def test_parse_ok_full() -> None:
    """REQ-ADS-FR-002：合法输入被规范化，user_tags 去重保序。"""
    s = parse_scene(
        {"time_slot": "night", "device": "mobile", "user_tags": ["student", "student", "gamer"]}
    )
    assert s.time_slot == "night"
    assert s.device == "mobile"
    assert s.user_tags == ("student", "gamer")  # 去重保序


def test_parse_ok_without_tags() -> None:
    """REQ-ADS-FR-002：user_tags 可省略，默认为空元组。"""
    s = parse_scene({"time_slot": "morning", "device": "desktop"})
    assert s.user_tags == ()


def test_parse_reject_missing_field() -> None:
    """REQ-ADS-FR-002（反例）：缺必填字段必须拒绝，不进入 LLM。"""
    with pytest.raises(SceneInputError, match="不合法"):
        parse_scene({"time_slot": "night"})


def test_parse_reject_invalid_time_slot() -> None:
    """REQ-ADS-FR-002（反例）：非法 time_slot 枚举必须拒绝。"""
    with pytest.raises(SceneInputError):
        parse_scene({"time_slot": "midnight", "device": "mobile"})


def test_parse_reject_invalid_device() -> None:
    """REQ-ADS-FR-002（反例）：非法 device 枚举必须拒绝。"""
    with pytest.raises(SceneInputError):
        parse_scene({"time_slot": "night", "device": "pc"})


def test_parse_reject_non_dict() -> None:
    """REQ-ADS-FR-002（反例）：非 JSON 对象的输入必须拒绝。"""
    with pytest.raises(SceneInputError, match="JSON 对象"):
        parse_scene("night")


def test_parse_reject_extra_field() -> None:
    """REQ-ADS-FR-002（反例）：多余字段必须拒绝（additionalProperties=false，防隐秘维度）。"""
    with pytest.raises(SceneInputError):
        parse_scene({"time_slot": "night", "device": "mobile", "location": "hk"})


def test_parse_reject_bad_tags_type() -> None:
    """REQ-ADS-FR-002（反例）：user_tags 类型错误必须拒绝。"""
    with pytest.raises(SceneInputError):
        parse_scene({"time_slot": "night", "device": "mobile", "user_tags": "student"})
