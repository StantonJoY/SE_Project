"""把语料条目投影成合法 `Ad`，扩展信息走旁路（REQ-ADS-FR-010 / INV-V3-001）。

Implements: ADR-006 D3（Ad 复用、扩展信息不进 AD_SCHEMA）
Verifies: REQ-ADS-FR-010（ad_id 合成 + category 三级兜底）、INV-V3-001

关键设计：**不新建 CorpusAd 类型**。spike 实测 30/30 可以通过 `AD_SCHEMA` 与 `AdRepository`——
`ad_id` 由 `item_id` 合成即可满足 `^ad_[0-9]+$`；七维标签、内容标识、年龄放在并行的
`CorpusFacts` 里，随管道流转但不进 Ad。这样 `ads/` 与 `AD_SCHEMA` **一个字都不用改**。
"""

from __future__ import annotations

from ads.models import Ad, SceneRestrictions

from .models import CorpusFacts, CorpusItem

#: category 三级兜底的最后一档
UNCATEGORIZED = "Uncategorized"

#: 进 target_tags 的维度（warnings 是合规信号，不进候选匹配）
_TARGET_TAG_DIMENSIONS = ("theme", "mechanics", "mood", "audience")
_MAX_TARGET_TAGS = 8


def _category_for(item: CorpusItem) -> str:
    """三级兜底：tags.genre[0] → items.genres[0] → Uncategorized。

    实测：241930 与 71250 的 `genres` 为空，但 `tags.genre` 有值——
    这正是"真实数据有坑"的第一处，兜底必须存在（REQ-ADS-FR-010）。
    """
    for candidate in item.tags.get("genre", ()):
        if candidate.strip():
            return candidate
    for candidate in item.genres:
        if candidate.strip():
            return candidate
    return UNCATEGORIZED


def _target_tags(item: CorpusItem) -> list[str]:
    tags: list[str] = []
    for dim in _TARGET_TAG_DIMENSIONS:
        for value in item.tags.get(dim, ()):
            if value not in tags:
                tags.append(value)
    return tags[:_MAX_TARGET_TAGS]


def corpus_to_ad(item: CorpusItem) -> tuple[Ad, CorpusFacts]:
    """投影单条语料：返回**合法的 Ad** 与需要旁路传递的事实。"""
    ad = Ad(
        ad_id=f"ad_{item.item_id}",
        title=item.name,
        copy=item.summary or item.name,
        category=_category_for(item),
        target_tags=_target_tags(item),
        # 语料没有"素材级场景限制"，默认全放开；场景约束由合规层判定
        scene_restrictions=SceneRestrictions(not_night=False, not_campus=False, allowed_devices=[]),
        banned_check="checked",
    )
    facts = CorpusFacts(
        item_id=item.item_id,
        content_descriptors=item.content_descriptors,
        content_warnings=item.content_warnings,
        required_age=item.required_age,
    )
    return ad, facts


def project_all(items: list[CorpusItem]) -> tuple[list[Ad], dict[str, CorpusFacts]]:
    """批量投影。返回 (广告列表, ad_id → 事实) —— 供 pipeline 与合规层使用。"""
    ads: list[Ad] = []
    facts: dict[str, CorpusFacts] = {}
    for item in items:
        ad, item_facts = corpus_to_ad(item)
        ads.append(ad)
        facts[ad.ad_id] = item_facts
    return ads, facts
