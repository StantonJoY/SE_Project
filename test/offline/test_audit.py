"""证据子系统与 monitor 登记册的离线测试。

Verifies: REQ-ADS-GOV-001（审计证据，恰好 1 条）、REQ-ADS-AI-002（版本溯源）、
          REQ-ADS-NFR-QA-002（monitor 具体可度量）、
          INV-ADS-012（恰好 1 条完整审计证据）。
批准：docs/test-approvals.yaml 的 TA-0003（⚠️ 批准晚于实现，见 TD-023）。
运行：仓库根目录下 pytest test/offline/test_audit.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from audit import (
    METRIC_REGISTRY,
    AuditError,
    AuditRecordBuilder,
    AuditWriteError,
    FailingAuditStore,
    InMemoryAuditStore,
    JsonlAuditStore,
    MetricDefinition,
    MetricSnapshot,
    metric_names,
    new_audit_id,
)

# ---- 恰好一条（INV-ADS-012 的结构保证） ----

def test_write_once_succeeds() -> None:
    """REQ-ADS-GOV-001：一次 write 恰好产生 1 条记录。"""
    store = InMemoryAuditStore()
    rec = AuditRecordBuilder(audit_id="aud-1", store=store)
    rec.add(scene={"time_slot": "night"})
    assert rec.write(final={"kind": "ad"}) == "aud-1"
    assert store.count == 1
    assert rec.written is True


def test_second_write_is_rejected() -> None:
    """INV-ADS-012（反例）：同一请求写第二次必须被拒绝——使"2 条"结构上不可能。"""
    store = InMemoryAuditStore()
    rec = AuditRecordBuilder(audit_id="aud-2", store=store)
    rec.write()
    with pytest.raises(AuditError, match="只允许 1 条"):
        rec.write()
    assert store.count == 1, "第二次写入不得落盘"


def test_record_contains_audit_id_and_timestamp() -> None:
    """REQ-ADS-GOV-001：记录必须含审计 ID 与 ISO 8601 时间戳（可追溯）。"""
    store = InMemoryAuditStore()
    AuditRecordBuilder(audit_id="aud-3", store=store).write()
    rec = store.records[0]
    assert rec["audit_id"] == "aud-3"
    assert "timestamp" in rec and "T" in rec["timestamp"]


def test_new_audit_id_is_unique() -> None:
    """REQ-ADS-GOV-001：审计 ID 必须唯一（否则证据无法一一对应）。"""
    ids = {new_audit_id() for _ in range(200)}
    assert len(ids) == 200


def test_audit_store_has_no_read_api() -> None:
    """memory-design.md §2 S1（反例）：审计存储**不得**提供读取接口。

    结构上禁止"决策路径回读审计历史"——回读会引入隐藏状态，
    使同一输入在不同历史下产出不同决策（违反无状态设计）。
    """
    public = {n for n in dir(JsonlAuditStore) if not n.startswith("_")}
    assert public == {"append", "path"}, f"审计存储暴露了预期外的接口: {public}"


# ---- 写入失败即整体失败（ADR-002 D2） ----

def test_failing_store_raises_audit_write_error() -> None:
    """INV-ADS-012 / ADR-002 D2：写入失败必须抛 AuditWriteError，**绝不吞掉**。"""
    with pytest.raises(AuditWriteError, match="注入的审计故障"):
        AuditRecordBuilder(audit_id="aud-4", store=FailingAuditStore()).write()


def test_write_failure_does_not_mark_written() -> None:
    """INV-ADS-012：写入失败后不得标记为已写 —— 否则调用方会误以为有证据。"""
    rec = AuditRecordBuilder(audit_id="aud-5", store=FailingAuditStore())
    with pytest.raises(AuditWriteError):
        rec.write()
    assert rec.written is False


# ---- JSONL 实现 ----

def test_jsonl_store_appends_valid_json_lines() -> None:
    """REQ-ADS-GOV-001：JSONL 实现必须产出可逐行解析的 JSON。

    不依赖 pytest `tmp_path`（受限沙箱下子进程无法建临时目录）；
    改为在文件 I/O 边界打桩，断言写入的字节内容。
    """
    written: list[str] = []

    class _FakeFile:
        def __enter__(self) -> _FakeFile:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def write(self, text: str) -> int:
            written.append(text)
            return len(text)

    import audit.store as store_mod

    real_open, real_mkdir = open, Path.mkdir
    store = JsonlAuditStore("virtual/dir/audit.jsonl")
    try:
        store_mod.open = lambda *a, **k: _FakeFile()  # type: ignore[assignment]
        Path.mkdir = lambda self, **k: None  # type: ignore[assignment]
        store.append({"audit_id": "aud-6", "kind": "ad"})
        store.append({"audit_id": "aud-7", "kind": "no_ad"})
    finally:
        store_mod.open = real_open  # type: ignore[assignment]
        Path.mkdir = real_mkdir  # type: ignore[assignment]

    assert len(written) == 2
    parsed = [json.loads(line) for line in written]
    assert [p["audit_id"] for p in parsed] == ["aud-6", "aud-7"]
    assert all(line.endswith("\n") for line in written), "每条记录须以换行结尾（JSONL 规范）"


def test_jsonl_store_wraps_oserror() -> None:
    """ADR-002 D2：底层 OSError 必须转换为 AuditWriteError（契约统一，不泄漏实现细节）。"""
    real_mkdir = Path.mkdir
    store = JsonlAuditStore("virtual/audit.jsonl")
    try:
        def boom(self, **k):  # noqa: ANN001, ANN202
            raise OSError("模拟磁盘故障")

        Path.mkdir = boom  # type: ignore[assignment]
        with pytest.raises(AuditWriteError, match="审计写入失败"):
            store.append({"a": 1})
    finally:
        Path.mkdir = real_mkdir  # type: ignore[assignment]


# ---- monitor 登记册 ----

def test_registry_is_non_empty_and_unique() -> None:
    """REQ-ADS-NFR-QA-002：monitor 登记册非空且名称唯一。"""
    names = metric_names()
    assert len(names) >= 20, f"追踪矩阵声明了 22 条 monitor，实际登记 {len(names)} 条"
    assert len(set(names)) == len(names), "monitor 名称必须唯一"


def test_every_metric_has_requirement_and_invariant() -> None:
    """REQ-ADS-NFR-QA-002：每条 monitor 必须追溯到 REQ 与 INV（否则是孤儿指标）。"""
    for m in METRIC_REGISTRY:
        assert m.requirement.startswith("REQ-ADS-"), f"{m.name} 缺 REQ 追溯"
        assert m.invariant.startswith("INV-ADS-"), f"{m.name} 缺 INV 追溯"
        assert m.direction in {"at_most", "at_least", "exactly"}, f"{m.name} direction 非法"


def test_snapshot_rejects_unregistered_metric() -> None:
    """REQ-ADS-NFR-QA-002（反例）：未登记的指标名必须被拒绝 —— 防止监控口径漂移。

    本测试的存在理由：实现 P5 时我误用了 `llm_output_parse_failure_count`
    （登记册中的名称是 `..._rate`），正是这条机制当场抓到了该错误。
    """
    snap = MetricSnapshot()
    with pytest.raises(KeyError, match="未登记"):
        snap.record("llm_output_parse_failure_count", 1)
    with pytest.raises(KeyError, match="未登记"):
        snap.increment("totally_made_up_metric")


def test_snapshot_violations_detects_threshold_breach() -> None:
    """INV-ADS-001：`compliance_escape_count > 0` 必须被识别为违规（最重要的 monitor）。"""
    snap = MetricSnapshot()
    snap.record("compliance_escape_count", 0)
    assert snap.violations() == []
    snap.record("compliance_escape_count", 1)
    v = snap.violations()
    assert v and "compliance_escape_count" in v[0]
    assert "INV-ADS-001" in v[0]


def test_snapshot_increment_accumulates() -> None:
    """REQ-ADS-GOV-001：累计型指标必须正确累加。"""
    snap = MetricSnapshot()
    for _ in range(3):
        snap.increment("no_ad_count")
    assert snap.values["no_ad_count"] == 3


@pytest.mark.parametrize(
    ("direction", "threshold", "ok", "bad"),
    [
        ("at_most", 5, 5, 6),
        ("at_least", 5, 5, 4),
        ("exactly", 1, 1, 0),
    ],
)
def test_metric_is_ok_boundaries(direction, threshold, ok, bad) -> None:
    """REQ-ADS-NFR-QA-002：三种 direction 的**边界值**判定必须正确（含等号）。"""
    m = MetricDefinition("m", "REQ-ADS-X-001", "INV-ADS-001", threshold, direction, "d")
    assert m.is_ok(ok) is True, f"{direction} 在边界 {ok} 应通过"
    assert m.is_ok(bad) is False, f"{direction} 在 {bad} 应失败"
