"""语料段落的配置与启动期校验（REQ-ADS-NFR-COST-002）。

Verifies: REQ-ADS-NFR-COST-002（K 上限由上下文预算反推）
Implements: ADR-006 D2/D5

`config.yaml` 的 `corpus` 段由本模块解析，**不塞进 `app.config.AppConfig`**：
语料是第 9 个元素，配置也应由它自己负责，避免 `app` 反向依赖语料内部结构。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

#: K 的硬上限。依据 spike：K=30 → 1,152 token（预算 2,000 的 58%）；
#: K=60 → 2,162 token（108%）直接触发 budget_exceeded。留出 40–50 的余量。
MAX_TOP_K = 50


class CorpusConfigError(Exception):
    """语料配置缺失或非法（启动期 fail loudly，不静默取默认值）。"""


@dataclass(frozen=True)
class CorpusConfig:
    items_path: str
    tags_path: str
    top_k: int = 30
    budget_impressions: int = 20
    tag_mapping: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    content_rules_path: str = "data/scene-content-rules.yaml"

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> CorpusConfig:
        data = dict(raw or {})
        mapping_raw = data.get("tag_mapping") or {}
        if not isinstance(mapping_raw, Mapping):
            raise CorpusConfigError("corpus.tag_mapping 必须是映射（场景取值 → 标签数组）")
        mapping: dict[str, tuple[str, ...]] = {}
        for key, values in mapping_raw.items():
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                raise CorpusConfigError(f"corpus.tag_mapping.{key} 必须是非空字符串数组")
            mapping[str(key)] = tuple(values)
        config = cls(
            items_path=str(data.get("items_path", "data/corpus/items.jsonl")),
            tags_path=str(data.get("tags_path", "data/corpus/tags.jsonl")),
            top_k=data.get("top_k", 30),
            budget_impressions=data.get("budget_impressions", 20),
            tag_mapping=mapping,
            content_rules_path=str(
                data.get("content_rules_path", "data/scene-content-rules.yaml")
            ),
        )
        config.validate()
        return config

    def validate(self) -> None:
        errors: list[str] = []
        for label, value in (
            ("items_path", self.items_path),
            ("tags_path", self.tags_path),
            ("content_rules_path", self.content_rules_path),
        ):
            if not isinstance(value, str) or not value.strip():
                errors.append(f"corpus.{label} 不得为空")
        if type(self.top_k) is not int or not (1 <= self.top_k <= MAX_TOP_K):
            errors.append(f"corpus.top_k={self.top_k!r} 必须为 1..{MAX_TOP_K} 的整数")
        if type(self.budget_impressions) is not int or self.budget_impressions <= 0:
            errors.append(f"corpus.budget_impressions={self.budget_impressions!r} 必须为正整数")
        if errors:
            raise CorpusConfigError("语料配置校验失败：\n  - " + "\n  - ".join(errors))


def load_corpus_config(path: str | Path) -> CorpusConfig:
    """从 `config.yaml` 读取 `corpus` 段；缺段即用默认值，非法值即拒绝启动。"""
    p = Path(path)
    if not p.exists():
        raise CorpusConfigError(f"配置文件不存在: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CorpusConfigError(f"配置文件不是合法 YAML: {p} ({exc})") from exc
    if not isinstance(raw, Mapping):
        raise CorpusConfigError(f"配置文件顶层必须是映射: {p}")
    return CorpusConfig.from_mapping(raw.get("corpus"))
