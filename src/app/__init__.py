"""编排与降级层（架构元素 ⑦）。

Implements: ADR-001（AI 建议 → 确定性裁决的接线）
            ADR-002 D1（降级终态统一为 no_ad）、D2（审计失败 → 整体失败）
Verifies: REQ-ADS-FR-003、REQ-ADS-FR-004、REQ-ADS-NFR-SAFETY-005、
          REQ-ADS-NFR-PERF-001、REQ-ADS-SEC-001

模块边界（对齐 AGENTS.md ④ 模块组织表）：
  · `pipeline.py` —— `recommend()` 编排 + 全部降级路径（元素本身）
  · `cli.py`      —— argparse 入口（元素本身）
  · `sanitize.py` —— pre-model 注入门（元素本身）
  · `config.py`   —— 配置加载与**启动期校验**（`pipeline.py` 的支撑；见 debt-register 的说明）
"""

from __future__ import annotations

from .config import (
    AppConfig,
    AuditConfig,
    ConfigError,
    DataConfig,
    EvalConfig,
    LLMConfig,
    SelectorConfig,
)
from .pipeline import Recommendation, recommend
from .sanitize import SanitizeResult, patterns, scan_for_injection

__all__ = [
    "recommend",
    "Recommendation",
    # 配置
    "AppConfig",
    "LLMConfig",
    "SelectorConfig",
    "AuditConfig",
    "DataConfig",
    "EvalConfig",
    "ConfigError",
    # 注入门
    "scan_for_injection",
    "SanitizeResult",
    "patterns",
]
