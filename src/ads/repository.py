"""素材库仓库：加载、查询、场景预筛（REQ-001/002）。"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .models import Ad
from .schema import AD_SCHEMA


class AdLoadError(Exception):
    """素材加载失败：文件不存在、JSON 非法、schema 不合法、ad_id 重复。"""


class AdRepository:
    def __init__(self, ads: list[Ad]) -> None:
        self._ads: dict[str, Ad] = {ad.ad_id: ad for ad in ads}

    # ---- 加载 ----

    @classmethod
    def load(cls, path: str | Path) -> "AdRepository":
        """从 JSON 文件加载素材库（REQ-001/002）。

        逐条 schema 校验，任一不合法即抛 AdLoadError；
        校验通过后 ad_id 必须唯一，重复即抛 AdLoadError。
        """
        p = Path(path)
        if not p.exists():
            raise AdLoadError(f"素材文件不存在: {p}")
        try:
            with open(p, encoding="utf-8") as f:
                raw_items = json.load(f)
        except json.JSONDecodeError as e:
            raise AdLoadError(f"素材文件不是合法 JSON: {p} ({e})") from e
        if not isinstance(raw_items, list):
            raise AdLoadError(f"素材文件顶层必须是数组: {p}")

        ads: list[Ad] = []
        seen: set[str] = set()
        for i, item in enumerate(raw_items):
            try:
                jsonschema.validate(instance=item, schema=AD_SCHEMA)
            except jsonschema.ValidationError as e:
                raise AdLoadError(f"第 {i + 1} 条素材不合法（REQ-002）: {e.message}") from e
            ad = Ad.from_dict(item)
            if ad.ad_id in seen:
                raise AdLoadError(f"ad_id 重复（REQ-001）: {ad.ad_id}")
            seen.add(ad.ad_id)
            ads.append(ad)

        return cls(ads)

    # ---- 查询 ----

    @property
    def count(self) -> int:
        return len(self._ads)

    def all(self) -> list[Ad]:
        return list(self._ads.values())

    def get(self, ad_id: str) -> Ad | None:
        return self._ads.get(ad_id)

    # ---- 场景预筛（规则预筛：素材自身声明的硬约束，REQ-009 前置） ----

    def filter_by_scene(self, scene) -> list[Ad]:
        """剔除与场景硬约束冲突的候选。

        依赖 duck-typing 的 scene 对象：须有 `time_slot`、`device`、`user_tags` 属性。
        校园信号 = user_tags 包含 "student"。
        """
        result: list[Ad] = []
        is_campus = "student" in (scene.user_tags or [])
        for ad in self.all():
            r = ad.scene_restrictions
            if r.not_night and scene.time_slot == "night":
                continue
            if r.not_campus and is_campus:
                continue
            if r.allowed_devices and scene.device not in r.allowed_devices:
                continue
            result.append(ad)
        return result
