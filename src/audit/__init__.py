"""审计子系统。

Implements: ADR-002 D2（审计不可协商；写入失败 → 整体失败）
Enforces: INV-ADS-012（每次请求恰好 1 条完整审计证据）
Verifies: REQ-ADS-GOV-001、REQ-ADS-AI-002

模块边界（架构元素 ⑥「证据子系统」）：
  · `store.py`   —— 审计存储（JSONL 追加写 / 内存 / 故障注入）+ 恰好一次的构造器
  · `metrics.py` —— 运行时 monitor 的登记册（22 条，来源 trace-matrix §1）
"""

from __future__ import annotations

from .metrics import (
    METRIC_REGISTRY,
    MetricDefinition,
    MetricSnapshot,
    metric_names,
)
from .store import (
    AuditError,
    AuditRecordBuilder,
    AuditStore,
    AuditWriteError,
    FailingAuditStore,
    InMemoryAuditStore,
    JsonlAuditStore,
    new_audit_id,
)

__all__ = [
    # 存储
    "AuditStore",
    "JsonlAuditStore",
    "InMemoryAuditStore",
    "FailingAuditStore",
    "AuditRecordBuilder",
    "AuditError",
    "AuditWriteError",
    "new_audit_id",
    # monitor
    "METRIC_REGISTRY",
    "MetricDefinition",
    "MetricSnapshot",
    "metric_names",
]
