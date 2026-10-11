"""合规检查结果模型（CheckResult / ComplianceVerdict）。

Implements: ADR-001（确定性 compliance 管道为 FINAL AUTHORITY）
            ADR-002 D1（降级终态 no_ad，fail-closed）
Enforces: INV-ADS-001（未经确定性合规过滤的广告绝不被展示）
Verifies: REQ-ADS-NFR-SAFETY-001（零逃逸）
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """单项合规检查结果。"""

    ok: bool
    rule: str        # 规则标识：output_exists / banned_words / category / scene
    detail: str = ""  # 失败细节（命中词、品类、约束等）


@dataclass(frozen=True)
class ComplianceVerdict:
    """整个合规管道的裁决（REQ-006：展示的广告必须全部通过）。"""

    approved: bool
    results: tuple[CheckResult, ...]

    def rejected_rule(self) -> str | None:
        """返回第一个失败的规则标识；全部通过返回 None。"""
        for r in self.results:
            if not r.ok:
                return r.rule
        return None

    def detail_of(self, rule: str) -> str | None:
        for r in self.results:
            if r.rule == rule:
                return r.detail
        return None
