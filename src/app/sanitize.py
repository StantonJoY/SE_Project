"""pre-model 注入中和门（REQ-ADS-SEC-001 / INV-ADS-005）。

Implements: ADR-001（AI 之前的确定性边界；课程 SEC-001 "sanitize before model"）
            runtime-policy-catalog.md RP-003
Enforces: INV-ADS-005（已知注入模式绝不在未中和的情况下抵达 LLM）
Verifies: REQ-ADS-SEC-001（注入样本 100% 被拦截或中和）

**攻击面与对策（诚实分析）**

本项目的**场景输入**是强约束的结构化数据（时段/设备是枚举，标签是短字符串），
注入面很小。真实攻击面在**素材文本**：`data/ads.json` 的 `title` / `copy`
会被渲染进 prompt 的 RETRIEVED 层。因此本门检查的是**装配后的整段 prompt**
（SYSTEM/USER 层是固定常量，实际可变部分就是候选文本）。

**处置：检出即拒绝，不尝试"清洗后继续"**

这是刻意的选择（fail-closed）：
  · 素材文本的任何可疑内容都由**人工入库流程**处理，不在运行期"改写后放行"——
    改写会让"哪一条被改过"失去可追溯性，而本项目的审计要求原始证据完整。
  · 因此本门返回命中详情，`app.pipeline` 据此降级为 `no_ad`（原因码 `injection_detected`），
    并记录**原始文本**供回归（RP-003）。

**检测精度取向**：宁可**漏检措辞变体**，也不误伤正常广告文案。
因此模式集为**高精度**（明确的指令覆盖/角色扮演/越狱措辞），并由测试约束误报率。
本门是防线之一，不是唯一防线 —— 真正的安全保证来自"闭集选择 + 严格 schema 解析"
（`INV-ADS-002`/`INV-ADS-003`），即**即使注入成功也拿不到权威**。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 高精度注入模式（中英双语）。刻意保守：只收录几乎不可能是正常广告文案的措辞。
_INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ignore_previous", r"ignore\s+(?:all\s+)?(?:the\s+)?previous\s+instructions?"),
    ("disregard_above", r"disregard\s+(?:all\s+)?(?:the\s+)?(?:above|previous)"),
    ("ignore_zh", r"忽略(?:上述|以上|之前|前面)(?:的)?(?:所有)?(?:指令|要求|提示|规则)"),
    ("system_prompt_probe", r"(?:print|reveal|show|repeat)\s+(?:your\s+)?system\s+prompt"),
    ("leak_prompt_zh", r"(?:输出|显示|打印|重复)(?:你的)?(?:系统|初始)(?:提示词|prompt|指令)"),
    ("role_override", r"you\s+are\s+now\s+(?:a|an)\s+"),
    ("role_override_zh", r"你现在(?:是|扮演)"),
    ("jailbreak_dan", r"\bDAN\b|developer\s+mode"),
    ("override_output", r"override\s+(?:the\s+)?(?:output|schema|json)"),
    ("override_zh", r"(?:绕过|跳过)(?:合规|过滤|检查|审核)"),
)

_COMPILED: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _INJECTION_PATTERNS
)


@dataclass(frozen=True)
class SanitizeResult:
    """注入门的结果。"""

    clean: bool
    pattern_id: str = ""
    matched_text: str = ""
    detail: str = ""


def scan_for_injection(text: str) -> SanitizeResult:
    """扫描文本中的已知注入模式（纯函数，无 IO）。

    返回命中的**第一个**模式（按 `_INJECTION_PATTERNS` 声明顺序，确定性）。
    """
    for pattern_id, regex in _COMPILED:
        m = regex.search(text)
        if m:
            return SanitizeResult(
                clean=False,
                pattern_id=pattern_id,
                matched_text=m.group(0),
                detail=f"prompt 中命中注入模式 {pattern_id!r}: {m.group(0)!r}",
            )
    return SanitizeResult(clean=True)


def patterns() -> tuple[str, ...]:
    """已登记的注入模式 ID（供测试与审计核对）。"""
    return tuple(name for name, _ in _INJECTION_PATTERNS)
