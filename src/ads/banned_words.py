"""违禁词表加载与检查（REQ-008：含违禁词的广告禁止展示）。"""

from __future__ import annotations

import json
from pathlib import Path


class BannedWords:
    """违禁词表。check() 对文本做子串匹配，命中返回该词，未命中返回 None。"""

    def __init__(self, words: list[str]) -> None:
        # 归一化：去空串、去重、保序
        seen: set[str] = set()
        cleaned: list[str] = []
        for w in words:
            w = w.strip().lower()
            if w and w not in seen:
                seen.add(w)
                cleaned.append(w)
        self._words: tuple[str, ...] = tuple(cleaned)

    @property
    def words(self) -> tuple[str, ...]:
        return self._words

    @classmethod
    def load(cls, path: str | Path) -> "BannedWords":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not all(isinstance(w, str) for w in data):
            raise ValueError(f"违禁词表格式错误（须为字符串数组）: {path}")
        return cls(data)

    def check(self, text: str) -> str | None:
        """返回命中的最长违禁词（更具体）；未命中返回 None。"""
        lowered = text.lower()
        hits = [w for w in self._words if w in lowered]
        if not hits:
            return None
        return max(hits, key=len)

    def check_all(self, *texts: str) -> str | None:
        for text in texts:
            hit = self.check(text)
            if hit is not None:
                return hit
        return None
