"""固定评估集与 replay runner（架构资产 ⑧，非 `src/` 元素）。

Implements: ADR-003（评估集为一等架构资产：判定口径、分母分离、阈值语义）
            ASR-ADS-15（固定评估集 + replay runner，作 CI 阻断门）
Enforces: INV-ADS-016（评估门：阈值失败必须阻断后续）
Verifies: REQ-ADS-NFR-QA-001（≥20 条、一键 replay、输出通过率与违规数）、
          REQ-ADS-NFR-PERF-001（p95 延迟与 SLA drift 的观测窗口）

**权威级别 = 只读验证资产**（ADR-003 D1）：**不参与运行时"是否展示"的裁决**，
只在 CI 中判定合并可否放行。

模块边界：
  · `eval_cases.json` —— 评估集数据（≥20 条，五类；每条含 basis + anchors）
  · `eval_runner.py`  —— 加载（fail-closed 校验）+ replay（**完整管道**）+ 报告 + 退出码

**blindness 对偶**（ADR-003 D7）：评估集不由被测实现的输出反向生成，
且运行时不可见（`src/` 下任何模块均不 import `eval`）。
"""

from __future__ import annotations

from .eval_runner import (
    EvalCase,
    EvalDataError,
    ReplayReport,
    load_cases,
    main,
    replay,
)

__all__ = [
    "load_cases",
    "replay",
    "main",
    "EvalCase",
    "EvalDataError",
    "ReplayReport",
]
