"""证据子系统：JSONL 审计日志（REQ-ADS-GOV-001）。

Implements: ADR-002 D2（审计不可协商；写入失败 → 本次推荐整体失败，fail-closed）
            memory-design.md §2 S1（审计**只写不读**——决策路径禁止回读历史）
Enforces: INV-ADS-012（每次推荐请求恰好 1 条完整审计证据）
Verifies: REQ-ADS-GOV-001、REQ-ADS-AI-002（版本溯源）

三条结构性质（不靠约定）：
  1. **只写不读** —— 本模块的公开 API 只有写入与计数，**没有读取接口**。
     回读会让过去的证据反过来影响现在的决策（引入隐藏状态）。
  2. **恰好一次** —— `AuditRecordBuilder` 保证每个请求只落一条；
     二次写入抛错（`AuditError`），使"0 条或 2 条"在结构上不可能。
  3. **失败即整体失败** —— 写入异常向上抛，调用方（`app.pipeline`）据此降级，
     **绝不静默继续**（否则产生无证据决策）。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


class AuditError(Exception):
    """审计记录不完整，或同一请求被写入多于一次。"""


class AuditWriteError(Exception):
    """审计落盘失败（磁盘/权限/IO）。调用方必须据此整体失败（ADR-002 D2）。"""


@dataclass
class AuditRecordBuilder:
    """单次推荐请求的审计记录构造器（保证"恰好一条"）。

    用法：管道在流程中逐步 `add` 证据，结束时调用**一次** `write`。
    再次调用 `write` 抛 `AuditError` —— 使"2 条"不可能发生。
    """

    audit_id: str
    store: "AuditStore"
    fields: dict[str, Any] = field(default_factory=dict)
    _written: bool = field(default=False, init=False, repr=False)

    @property
    def written(self) -> bool:
        return self._written

    def add(self, **kwargs: Any) -> None:
        """补充证据字段（同名键以最后一次为准，便于流程中逐步完善）。"""
        self.fields.update(kwargs)

    def write(self, **kwargs: Any) -> str:
        """落盘恰好一条审计记录，返回 `audit_id`。"""
        if self._written:
            raise AuditError(f"审计记录 {self.audit_id} 已被写入 —— 每次请求只允许 1 条（INV-ADS-012）")
        self.fields.update(kwargs)
        record = {
            "audit_id": self.audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **self.fields,
        }
        self.store.append(record)
        self._written = True
        return self.audit_id


class AuditStore(Protocol):
    """审计存储的抽象边界。

    **刻意不提供 read/query 方法** —— 见模块 docstring 第 1 条。
    """

    def append(self, record: dict[str, Any]) -> None:
        """追加一条记录。失败须抛 `AuditWriteError`。"""
        ...  # pragma: no cover


class JsonlAuditStore:
    """JSONL 追加写实现（REQ-ADS-GOV-001）。

    · 追加写（`"a"`），**不覆盖** —— 符合 append-only 审计要求。
    · 父目录不存在时创建。
    · 任何 IO 失败 → `AuditWriteError`（**绝不吞掉**）。
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: dict[str, Any]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            raise AuditWriteError(f"审计写入失败（{self._path}）: {e}") from e


class InMemoryAuditStore:
    """内存实现（离线测试用；不触碰文件系统）。"""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, record: dict[str, Any]) -> None:
        self.records.append(record)

    @property
    def count(self) -> int:
        return len(self.records)


class FailingAuditStore:
    """总是失败的实现（用于验证"审计失败 → 整体失败"这条不变量）。"""

    def append(self, record: dict[str, Any]) -> None:
        raise AuditWriteError("注入的审计故障（测试用）")


def new_audit_id() -> str:
    """生成审计记录 ID（唯一；用于把"没广告"也变成可追溯事件）。"""
    return f"aud-{uuid.uuid4().hex[:12]}"
