"""场景输入解析（REQ-003：非法/缺失字段直接拒绝，不进入 LLM）。"""

from __future__ import annotations

import jsonschema

from .models import Scene
from .schema import SCENE_SCHEMA


class SceneInputError(Exception):
    """场景输入不合法：类型错误、缺字段、枚举越界、多余字段。"""


def parse_scene(raw) -> Scene:
    """把原始输入解析为规范化 Scene。

    校验失败抛 SceneInputError（含明确原因），调用方应直接拒绝该请求。
    """
    if not isinstance(raw, dict):
        raise SceneInputError(f"场景输入必须是 JSON 对象，实际为 {type(raw).__name__}")
    try:
        jsonschema.validate(instance=raw, schema=SCENE_SCHEMA)
    except jsonschema.ValidationError as e:
        raise SceneInputError(f"场景输入不合法（REQ-003）: {e.message}") from e

    # 规范化：user_tags 去重保序
    tags = raw.get("user_tags", [])
    seen: set[str] = set()
    cleaned: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            cleaned.append(t)
    return Scene(time_slot=raw["time_slot"], device=raw["device"], user_tags=tuple(cleaned))
