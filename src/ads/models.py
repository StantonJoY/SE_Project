"""Ad 数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SceneRestrictions:
    """广告自身声明的场景硬约束（REQ-009 的数据来源）。"""

    not_night: bool = False
    not_campus: bool = False
    allowed_devices: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> "SceneRestrictions":
        return cls(
            not_night=bool(raw.get("not_night", False)),
            not_campus=bool(raw.get("not_campus", False)),
            allowed_devices=list(raw.get("allowed_devices", [])),
        )


@dataclass(frozen=True)
class Ad:
    """一条广告素材。"""

    ad_id: str
    title: str
    copy: str
    category: str
    target_tags: list[str]
    scene_restrictions: SceneRestrictions
    banned_check: str = "pending"

    @classmethod
    def from_dict(cls, raw: dict) -> "Ad":
        return cls(
            ad_id=raw["ad_id"],
            title=raw["title"],
            copy=raw["copy"],
            category=raw["category"],
            target_tags=list(raw.get("target_tags", [])),
            scene_restrictions=SceneRestrictions.from_dict(raw["scene_restrictions"]),
            banned_check=raw.get("banned_check", "pending"),
        )
