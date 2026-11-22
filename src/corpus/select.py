"""确定性候选生成：场景标签映射 + 命中数排序（REQ-ADS-FR-011 / INV-V3-002）。

Verifies: REQ-ADS-FR-011（top-K、空匹配返回空）、INV-V3-002（纯函数、无状态）
Implements: ADR-006 D2（候选来自语料，不依赖 review_count 连续值）

排序规则（与输入顺序无关）：
  1. 命中标签数**降序**；
  2. 相同时按 `item_id` **升序**。
不读时间、随机数、审计历史——同一输入永远同一输出（双跑 diff = 0）。
"""

from __future__ import annotations

from collections.abc import Mapping

from .models import CorpusItem


def target_labels(scene, mapping: Mapping[str, tuple[str, ...]]) -> frozenset[str]:
    """把场景字段翻译成目标标签集合（小写化）。

    `mapping` 的键是场景取值（`night` / `mobile` / `student` …），值是标签数组；
    多个字段命中的标签取**并集**：场景越具体，召回越窄。
    """
    keys = [scene.time_slot, scene.device, *(scene.user_tags or [])]
    labels: set[str] = set()
    for key in keys:
        for value in mapping.get(str(key), ()):
            labels.add(value.lower())
    return frozenset(labels)


def select_candidates(
    scene, items: list[CorpusItem], mapping: Mapping[str, tuple[str, ...]], k: int,
) -> list[CorpusItem]:
    """返回命中最多的前 K 条语料；无命中返回空列表（**不硬凑**）。"""
    if type(k) is not int or k <= 0:
        raise ValueError(f"k 必须是正整数，实际为 {k!r}")
    targets = target_labels(scene, mapping)
    if not targets:
        return []

    scored: list[tuple[int, int, CorpusItem]] = []
    for item in items:
        hits = len(item.match_labels() & targets)
        if hits > 0:
            scored.append((-hits, item.item_id, item))
    scored.sort(key=lambda row: (row[0], row[1]))
    return [item for _, _, item in scored[:k]]
