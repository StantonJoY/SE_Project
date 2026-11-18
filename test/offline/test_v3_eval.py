"""V3 固定评估分区的回归测试（REQ-ADS-NFR-QA-006）。

Verifies: REQ-ADS-NFR-QA-006（V3 分区 ≥12 条、含负例、违规为 0）
Implements: ADR-006 D7

负例与逃逸判定由 `eval/v3_runner.py` 完成；本模块只断言"分区存在、能跑、不逃逸"。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

import v3_runner  # noqa: E402


def test_v3_partition_is_registered_and_sized():
    """REQ-ADS-NFR-QA-006：分区存在，用例数 ≥12，且至少 3 条负例。"""
    spec = json.loads((ROOT / "eval" / "v3_cases.json").read_text(encoding="utf-8"))
    assert spec["partition"] == "V3"
    cases = spec["cases"]
    assert len(cases) >= 12
    negatives = [c for c in cases if c.get("expect") == "no_ad"]
    assert len(negatives) >= 3


def test_v3_partition_passes_without_escaping():
    """REQ-ADS-NFR-QA-006 / INV-ADS-001：达成率达标、合规逃逸为 0、无崩溃。"""
    report = v3_runner.run()
    assert report["failures"] == []
    assert report["escapes"] == []
    assert report["pass_rate"] >= 0.95
    assert report["p95_sec"] < 5.0
