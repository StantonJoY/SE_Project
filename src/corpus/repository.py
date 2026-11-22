"""只读语料仓库：加载 `items.jsonl` + `tags.jsonl`，fail-closed。

Verifies: REQ-ADS-FR-009（只加载轻字段、行数一致）、INV-V3-001
Implements: ADR-006 D2（语料只读、与手写素材双源并存）

失败语义（与 `AdRepository` / `BannedWords` / `SceneRules` 对齐，见 `TD-014`）：
  1. 使用**专属异常** `CorpusLoadError`；
  2. 文件缺失 / JSONL 非法 / 顶层非对象 / 空语料 / 重复 item_id / 标签缺失 → 一律拒绝加载；
  3. 不做"尽量加载"的降级 —— 少一条语料比带一条脏语料安全。
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import TAG_DIMENSIONS, CorpusItem

#: 单条语料必须出现的字段（description_clean 刻意不在列，见 models.py）
_REQUIRED_ITEM_FIELDS = (
    "item_id",
    "name",
    "genres",
    "native_tags",
    "required_age",
    "content_descriptors",
    "review_count",
    "price_final",
    "is_free",
)


class CorpusLoadError(Exception):
    """语料加载失败：文件缺失、格式非法、空语料或标签缺失。"""


def _read_jsonl(path: Path, label: str) -> list[dict]:
    if not path.exists():
        raise CorpusLoadError(f"{label} 不存在: {path}")
    records: list[dict] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                text = line.strip()
                if not text:
                    continue
                try:
                    record = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise CorpusLoadError(f"{label} 第 {lineno} 行不是合法 JSON: {exc}") from exc
                if not isinstance(record, dict):
                    raise CorpusLoadError(f"{label} 第 {lineno} 行不是对象")
                records.append(record)
    except OSError as exc:
        raise CorpusLoadError(f"{label} 读取失败: {exc}") from exc
    if not records:
        raise CorpusLoadError(f"{label} 为空——空语料等同关闭召回，必须拒绝启动")
    return records


def _str_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise CorpusLoadError(f"{label} 必须是字符串数组")
    return tuple(value)


def _int(value: object, label: str) -> int:
    if type(value) is not int:
        raise CorpusLoadError(f"{label} 必须是整数（bool 不算）")
    return value


class CorpusRepository:
    """只读语料库。构造后不可变；`all()` 返回副本，调用方改不到内部状态。"""

    def __init__(self, items: list[CorpusItem]) -> None:
        self._items: tuple[CorpusItem, ...] = tuple(items)
        self._by_id: dict[int, CorpusItem] = {item.item_id: item for item in self._items}

    @classmethod
    def load(cls, items_path: str | Path, tags_path: str | Path) -> CorpusRepository:
        """加载两份 JSONL，按 item_id 一对一 join；任一环节不合法即整体拒绝。"""
        raw_items = _read_jsonl(Path(items_path), "items.jsonl")
        raw_tags = _read_jsonl(Path(tags_path), "tags.jsonl")

        tag_by_id: dict[int, dict] = {}
        for record in raw_tags:
            item_id = _int(record.get("item_id"), "tags.jsonl 的 item_id")
            if item_id in tag_by_id:
                raise CorpusLoadError(f"tags.jsonl 出现重复 item_id: {item_id}")
            tag_by_id[item_id] = record

        items: list[CorpusItem] = []
        seen: set[int] = set()
        for record in raw_items:
            for field in _REQUIRED_ITEM_FIELDS:
                if field not in record:
                    raise CorpusLoadError(f"items.jsonl 缺少字段 {field}")
            item_id = _int(record["item_id"], "item_id")
            if item_id in seen:
                raise CorpusLoadError(f"items.jsonl 出现重复 item_id: {item_id}")
            seen.add(item_id)
            if item_id not in tag_by_id:
                raise CorpusLoadError(f"tags.jsonl 缺少 item_id={item_id} 的标注")
            tags_raw = tag_by_id[item_id].get("tags")
            if not isinstance(tags_raw, dict):
                raise CorpusLoadError(f"item_id={item_id} 的 tags 必须是对象")
            tags = {
                dim: _str_tuple(tags_raw.get(dim, []), f"item_id={item_id} 的 tags.{dim}")
                for dim in TAG_DIMENSIONS
            }
            name = record["name"]
            if not isinstance(name, str) or not name.strip():
                raise CorpusLoadError(f"item_id={item_id} 的 name 必须是非空字符串")
            summary = record.get("summary") or tag_by_id[item_id].get("summary") or ""
            if not isinstance(summary, str):
                raise CorpusLoadError(f"item_id={item_id} 的 summary 必须是字符串")
            price_raw = record.get("price_final")
            if price_raw is not None and type(price_raw) is not int:
                raise CorpusLoadError(f"item_id={item_id} 的 price_final 必须是整数或 null")
            is_free = record.get("is_free")
            if not isinstance(is_free, bool):
                raise CorpusLoadError(f"item_id={item_id} 的 is_free 必须是布尔值")
            items.append(
                CorpusItem(
                    item_id=item_id,
                    name=name,
                    summary=summary,
                    genres=_str_tuple(record["genres"], f"item_id={item_id} 的 genres"),
                    native_tags=_str_tuple(record["native_tags"], f"item_id={item_id} 的 native_tags"),
                    required_age=_int(record["required_age"], f"item_id={item_id} 的 required_age"),
                    content_descriptors=tuple(
                        _int(v, f"item_id={item_id} 的 content_descriptors 元素")
                        for v in record["content_descriptors"]
                    ),
                    review_count=_int(record["review_count"], f"item_id={item_id} 的 review_count"),
                    tags=tags,
                    price_cents=price_raw,
                    is_free=is_free,
                )
            )
        return cls(sorted(items, key=lambda item: item.item_id))

    @property
    def count(self) -> int:
        return len(self._items)

    def all(self) -> list[CorpusItem]:
        return list(self._items)

    def get(self, item_id: int) -> CorpusItem | None:
        return self._by_id.get(item_id)
