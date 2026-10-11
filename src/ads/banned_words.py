"""违禁词表加载与检查。

Enforces: INV-ADS-007（含违禁词的广告绝不被展示）
Verifies: REQ-ADS-NFR-SAFETY-003（违禁词命中即 REJECT）
Implements: ADR-002 D4（banned_words.json 属 safety-critical 路径，改动须 ADR + 人工批准）

确定性要求：命中结果必须与词表文件中的出现顺序**无关**
（REQ-ADS-ARCH-004：确定性部分同输入同输出、逐位一致）。
"""

from __future__ import annotations

import json
from pathlib import Path


class BannedWordsLoadError(Exception):
    """违禁词表加载或格式错误（fail-closed：拒绝启动，不静默降级）。"""


class BannedWords:
    """违禁词表。check() 对文本做子串匹配，命中返回该词，未命中返回 None。

    命中选择规则（两级，顺序不可颠倒）：
      ① **最长优先** —— 更具体的命中更有诊断价值（'兼职刷单' 胜过 '刷单'）；
      ② **长度相同时取 Unicode 码点最小者** —— 使结果与词表存储顺序无关。

    ② 保证确定性（REQ-ADS-ARCH-004：同输入逐位一致）。注意这是**码点序**，
    不是中文拼音或笔画序；对中文两者不同（例如 博 U+535A < 赌 U+8D4C < 返 U+8FD4）。
    选码点序是因为它完全确定、不依赖语言环境或排序规则。
    """

    def __init__(self, words: list[str]) -> None:
        if not isinstance(words, list):
            raise TypeError(f"违禁词表必须是列表，实际为 {type(words).__name__}")
        cleaned: list[str] = []
        seen: set[str] = set()
        for w in words:
            if not isinstance(w, str):
                raise TypeError(f"违禁词必须是字符串，实际为 {type(w).__name__}: {w!r}")
            norm = w.strip().lower()
            if not norm:
                raise ValueError(f"违禁词不得为空或纯空白: {w!r}")
            if norm not in seen:
                seen.add(norm)
                cleaned.append(norm)
        self._words: tuple[str, ...] = tuple(cleaned)

    @property
    def words(self) -> tuple[str, ...]:
        return self._words

    @classmethod
    def load(cls, path: str | Path) -> BannedWords:
        """加载违禁词表（fail-closed）。

        与 AdRepository.load / SceneRules.load 保持一致的失败姿态：
        文件不存在、JSON 非法、顶层非数组、元素非字符串、表为空 —— 一律拒绝。
        """
        p = Path(path)
        if not p.exists():
            raise BannedWordsLoadError(f"违禁词表文件不存在: {p}")
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise BannedWordsLoadError(f"违禁词表不是合法 JSON: {p} ({e})") from e

        if not isinstance(data, list):
            raise BannedWordsLoadError(f"违禁词表顶层必须是数组: {p}")
        if not data:
            raise BannedWordsLoadError(
                f"违禁词表为空: {p} —— 空表意味着合规过滤形同虚设，拒绝启动（fail-closed）"
            )
        instance = cls(data)
        if not instance.words:
            raise BannedWordsLoadError(f"违禁词表归一化后为空: {p}")
        return instance

    def check(self, text: str) -> str | None:
        """返回命中的违禁词；未命中返回 None。

        选择规则：最长优先；长度相同时按字典序取最小（保证与词表顺序无关）。
        """
        lowered = text.lower()
        hits = [w for w in self._words if w in lowered]
        if not hits:
            return None
        # ① 最长优先；② 同长度取码点最小 → 与词表顺序无关（两级，不可颠倒）
        longest = max(len(w) for w in hits)
        return min(w for w in hits if len(w) == longest)

    def check_all(self, *texts: str) -> str | None:
        """按给定顺序检查多个文本，返回首个命中。"""
        for text in texts:
            hit = self.check(text)
            if hit is not None:
                return hit
        return None

