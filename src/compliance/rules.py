"""场景规则加载（data/scene_rules.json）。

- category_blacklist         敏感品类禁止展示（REQ-007）
- night_blocked_categories   夜间禁展示品类（REQ-009 规则级）
- campus_blocked_categories  校园禁展示品类（REQ-009 规则级）
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class SceneRulesLoadError(Exception):
    """场景规则文件加载或格式错误。"""


@dataclass(frozen=True)
class SceneRules:
    category_blacklist: tuple[str, ...] = ()
    night_blocked_categories: tuple[str, ...] = ()
    campus_blocked_categories: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: str | Path) -> "SceneRules":
        p = Path(path)
        if not p.exists():
            raise SceneRulesLoadError(f"规则文件不存在: {p}")
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise SceneRulesLoadError(f"规则文件不是合法 JSON: {p} ({e})") from e

        def _tuple(key: str) -> tuple[str, ...]:
            val = data.get(key, [])
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                raise SceneRulesLoadError(f"规则字段 {key!r} 必须为字符串数组")
            return tuple(val)

        return cls(
            category_blacklist=_tuple("category_blacklist"),
            night_blocked_categories=_tuple("night_blocked_categories"),
            campus_blocked_categories=_tuple("campus_blocked_categories"),
        )
