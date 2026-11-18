"""场景内容分级规则（REQ-ADS-NFR-SAFETY-008/009/010）。

Implements: ADR-006 D4（合规只做步骤内扩充，五步顺序不变）
Verifies: REQ-ADS-NFR-SAFETY-008（内容并集判据）、SAFETY-009（年龄兜底）、SAFETY-010（三档分级）

设计要点：
  · **判据是并集**：`content_warnings ∪ descriptor 映射标签`。
    只看 descriptors 会漏——实测全量 8,877 条 descriptors 为空但 warnings 非空
    （Among Us：descriptors=[]，warnings=[Violence, Blood]）。
  · **三档由场景标签决定**：`family`（严）/`campus`（中）/`competitive`（宽）；
    没有匹配标签时取 `default_tier`（campus）。
  · **年龄只作兜底**：全量 97% 的条目 `required_age = 0`（表示"无评级"），
    单靠年龄拦不住任何东西，所以它排在内容判据之后。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml


class ContentRulesError(Exception):
    """分级规则文件缺失或非法（启动期 fail loudly）。"""


class ContentFacts(Protocol):
    """合规层只需要这三个字段——不 import corpus，保持权威层不依赖数据层。"""

    content_descriptors: Sequence[int]
    content_warnings: Sequence[str]
    required_age: int


@dataclass(frozen=True)
class ContentTier:
    """一档场景的内容门槛。"""

    name: str
    block_labels: frozenset[str]
    max_age: int


@dataclass(frozen=True)
class ContentRules:
    """三档规则 + 场景映射 + descriptor 语义映射。"""

    tiers: Mapping[str, ContentTier]
    default_tier: str
    tag_to_tier: Mapping[str, str]
    descriptor_labels: Mapping[int, tuple[str, ...]]

    @classmethod
    def load(cls, path: str | Path) -> ContentRules:
        p = Path(path)
        if not p.exists():
            raise ContentRulesError(f"内容分级规则不存在: {p}")
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ContentRulesError(f"内容分级规则不是合法 YAML: {p} ({exc})") from exc
        if not isinstance(raw, dict):
            raise ContentRulesError(f"内容分级规则顶层必须是映射: {p}")

        tiers_raw = raw.get("tiers")
        if not isinstance(tiers_raw, dict) or not tiers_raw:
            raise ContentRulesError("tiers 不得为空")
        tiers: dict[str, ContentTier] = {}
        for name, spec in tiers_raw.items():
            if not isinstance(spec, dict):
                raise ContentRulesError(f"tier {name} 必须是映射")
            labels = spec.get("block_labels")
            max_age = spec.get("max_age")
            if not isinstance(labels, list) or any(not isinstance(x, str) for x in labels):
                raise ContentRulesError(f"tier {name}.block_labels 必须是字符串数组")
            if type(max_age) is not int or max_age < 0:
                raise ContentRulesError(f"tier {name}.max_age 必须是非负整数")
            tiers[str(name)] = ContentTier(str(name), frozenset(labels), max_age)

        default_tier = raw.get("default_tier")
        if default_tier not in tiers:
            raise ContentRulesError(f"default_tier={default_tier!r} 不在 tiers 中")

        tag_map_raw = raw.get("tag_to_tier") or {}
        if not isinstance(tag_map_raw, dict):
            raise ContentRulesError("tag_to_tier 必须是映射")
        tag_to_tier = {}
        for tag, tier_name in tag_map_raw.items():
            if tier_name not in tiers:
                raise ContentRulesError(f"tag_to_tier.{tag} 指向未知档位 {tier_name!r}")
            tag_to_tier[str(tag)] = str(tier_name)

        desc_raw = raw.get("descriptor_labels") or {}
        if not isinstance(desc_raw, dict):
            raise ContentRulesError("descriptor_labels 必须是映射")
        descriptor_labels: dict[int, tuple[str, ...]] = {}
        for key, labels in desc_raw.items():
            if type(key) is not int or not isinstance(labels, list):
                raise ContentRulesError(f"descriptor_labels[{key!r}] 必须是 int → 字符串数组")
            descriptor_labels[key] = tuple(str(x) for x in labels)

        return cls(
            tiers=tiers,
            default_tier=default_tier,
            tag_to_tier=tag_to_tier,
            descriptor_labels=descriptor_labels,
        )

    # ---- 场景 → 档位 ----
    def tier_for(self, scene) -> ContentTier:
        """按场景标签选档：命中最靠前的 user_tag 优先，其次 default。"""
        for tag in scene.user_tags or ():
            tier_name = self.tag_to_tier.get(str(tag))
            if tier_name is not None:
                return self.tiers[tier_name]
        return self.tiers[self.default_tier]

    # ---- 事实 → 内容标签（并集）----
    def labels_for(self, facts: ContentFacts) -> frozenset[str]:
        labels = {str(w) for w in facts.content_warnings}
        for code in facts.content_descriptors:
            labels.update(self.descriptor_labels.get(int(code), ()))
        return frozenset(labels)


@dataclass(frozen=True)
class ContentPolicy:
    """把"规则 + 每条广告的事实"打包成合规层的一个可选入参。"""

    rules: ContentRules
    facts: Mapping[str, ContentFacts]
