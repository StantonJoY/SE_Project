"""LLM 客户端接口与确定性 Mock。

Implements: ADR-001（AI 为 advisory；本层不裁决）
            ADR-005 原则（离线测试一律 MockLLM，真实 LLM 只在 live 测试）
Verifies: REQ-ADS-ARCH-004（Mock 必须确定性：同输入同输出）、REQ-ADS-ARCH-002（闭集）

设计要点：
  · `LLMClient.select()` 返回**原始文本**，不做任何解析 —— 解析是 `parser` 的职责。
    这使得"非法输出"可以被构造与测试，而不必真的调用一个坏模型。
  · `MockLLM` **确定性**：不读时钟、不用随机、不读环境变量。
  · `MockLLM` 只从 prompt 中出现的候选里挑（字典序最小），
    从而在离线测试中复现"闭集选择"的行为。
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from .types import CandidateBrief

# 从 prompt 中提取候选 ID 的模式（与 context.py 的渲染格式一致：`- ad_001 | ...`）
_CANDIDATE_LINE_RE = re.compile(r"^\s*-\s+(ad_\d+)\s*\|", re.MULTILINE)


def briefs_to_prompt_block(briefs: list[CandidateBrief]) -> str:
    """把候选摘要渲染为 prompt 中的一个块。

    格式固定为 `- <ad_id> | <category> | <title> | tags: ...`。
    **`MockLLM` 的解析正则与 `context.py` 的渲染都依赖本函数**，
    因此格式只有一处定义 —— 避免"渲染与解析漂移"（`BUG-007` 的同类教训）。
    """
    lines: list[str] = []
    for b in briefs:
        tags = ",".join(b.target_tags) if b.target_tags else "-"
        lines.append(f"- {b.ad_id} | {b.category} | {b.title} | tags: {tags}")
    return "\n".join(lines)


class LLMUnavailable(Exception):
    """LLM 不可用（超时 / 网络 / 鉴权）。

    上层捕获本异常后按 ADR-002 D1 降级为 `no_ad`（原因码 `llm_timeout` / `llm_error`）。
    """


@runtime_checkable
class LLMClient(Protocol):
    """AI 建议层的抽象边界。

    实现者可以是 `MockLLM`（离线）、未来的 OpenAI 兼容客户端（P8），
    或任何返回原始文本的东西。**协议不承诺输出合法** —— 合法性由 `parser` 校验。
    """

    def select(self, prompt: str) -> str:
        """对给定 prompt 返回 LLM 的原始文本响应。

        Raises:
            LLMUnavailable: 调用失败/超时。调用方应降级，不得继续。
        """
        ...  # pragma: no cover


class MockLLM:
    """确定性 mock LLM（离线测试与演示用）。

    行为（全部确定，无随机、无时钟依赖）：
      1. 若构造时指定 `fail_with`，则每次调用都抛出该异常（用于测试降级路径）。
      2. 否则从 prompt 中解析出候选 `ad_id` 列表，选**字典序最小**者。
      3. 若 prompt 中无候选，返回一个 `ad_id` 为空的合法 JSON ——
         交由 `parser` 因"不在候选集内"而拒绝（这正是闭集 gate 的作用）。

    Args:
        confidence: 固定返回的置信度（默认 0.85，高于阈值 0.5）。
        fail_with: 若非 None，则调用时抛出该异常实例。
        raw_override: 若非 None，则**原样返回该文本**（用于构造畸形输出）。
    """

    def __init__(
        self,
        *,
        confidence: float = 0.85,
        fail_with: Exception | None = None,
        raw_override: str | None = None,
    ) -> None:
        self._confidence = confidence
        self._fail_with = fail_with
        self._raw_override = raw_override

    def select(self, prompt: str) -> str:
        """返回确定性的原始响应文本（见类文档）。"""
        if self._fail_with is not None:
            raise self._fail_with
        if self._raw_override is not None:
            return self._raw_override

        ids = _CANDIDATE_LINE_RE.findall(prompt)
        chosen = min(ids) if ids else ""
        reason = (
            f"场景与「{chosen}」的目标标签匹配，且该候选在候选集中排序最前。"
            if chosen
            else "未在候选集中找到可选项。"
        )
        # 手工拼 JSON 而非 json.dumps：保证键顺序与分隔符固定（逐位可复现）
        return (
            "{"
            f'"ad_id": "{chosen}", '
            f'"reason": "{reason}", '
            f'"confidence": {self._confidence}'
            "}"
        )
