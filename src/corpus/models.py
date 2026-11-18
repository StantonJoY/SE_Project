"""语料条目的不可变模型（REQ-ADS-FR-009 / INV-V3-001）。

Verifies: REQ-ADS-FR-009（只加载轻字段）、REQ-ADS-ARCH-013（扩展信息走旁路）
Implements: ADR-006 D2/D3

**核心约束**：`CorpusItem` 不持有 `description_clean`。
该字段是 BM25/embedding 的输入（样本最长 8,007、全量最长 63,404 字符），
本轮候选生成走标签匹配，不需要它；不持有它，才能保证"进 prompt 的内容"可审计。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

#: 七维标签的固定键（与 `demo_steam_30` 的受控词表一致）
TAG_DIMENSIONS: tuple[str, ...] = (
    "genre",
    "theme",
    "mechanics",
    "art_style",
    "mood",
    "audience",
    "content_warnings",
)

#: 参与候选匹配的维度（`content_warnings` 是合规信号，不参与匹配）
MATCH_DIMENSIONS: tuple[str, ...] = TAG_DIMENSIONS[:-1]


@dataclass(frozen=True)
class CorpusItem:
    """一条只读语料（Steam 游戏元数据 + 七维标签）。"""

    item_id: int
    name: str
    summary: str
    genres: tuple[str, ...]
    native_tags: tuple[str, ...]
    required_age: int
    content_descriptors: tuple[int, ...]
    review_count: int
    tags: Mapping[str, tuple[str, ...]]
    #: 定价（美分）。`None` 表示"没有价格信息"，与"免费（0）"是**不同语义**（数据契约 §2 坑 1）。
    price_cents: int | None = None
    is_free: bool = False

    @property
    def content_warnings(self) -> tuple[str, ...]:
        """内容警告（来自 tags 层，缺失即空元组，不等同于"没有警告"）。"""
        return self.tags.get("content_warnings", ())

    def match_labels(self) -> frozenset[str]:
        """参与候选匹配的标签集合（小写化，七维去掉 warnings + native_tags）。"""
        labels: set[str] = {tag.lower() for tag in self.native_tags}
        for dim in MATCH_DIMENSIONS:
            labels.update(value.lower() for value in self.tags.get(dim, ()))
        return frozenset(labels)


@dataclass(frozen=True)
class CorpusFacts:
    """旁路事实：随 `Ad` 一起流转，但**不进** Ad 对象与 AD_SCHEMA（INV-V3-001）。

    合规层通过 `facts[ad_id]` 读取这些字段做内容分级；
    Ad 本身仍然是 schema 合法的纯广告契约。
    """

    item_id: int
    content_descriptors: tuple[int, ...]
    content_warnings: tuple[str, ...]
    required_age: int
