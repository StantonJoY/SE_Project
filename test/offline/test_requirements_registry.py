"""D1 需求注册表与架构输入一致性的离线测试。

Verifies: REQ-ADS-NFR-QA-002（每条 fit criterion ≥1 测试；每条不变量 ≥1 失败测试）、
          INV-ADS-011（验证完整性：无测试的 fit criterion 不得进入基线）、
          ADR-002 D3（验证治理）。
本模块同时是结构性约束 V1/V2/V3 的自身证据：它验证"注册表与不变量登记册必须双向一致"。
不使用 tmp_path（纯内存变异），因此在受限环境下也能运行。

运行：仓库根目录下 pytest test/offline/test_requirements_registry.py
"""

from __future__ import annotations

import copy
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts" / "validate_requirements.py"


def _load_validator():
    spec = spec_from_file_location("validate_requirements", VALIDATOR_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules["validate_requirements"] = module
    spec.loader.exec_module(module)
    return module


vr = _load_validator()


@pytest.fixture
def registry() -> dict:
    return vr.load_yaml(vr.REGISTRY_PATH)


@pytest.fixture
def schema() -> dict:
    return vr.load_json(vr.SCHEMA_PATH)


# ---- 正向：仓库中的注册表当前必须通过 ----

def test_registry_passes_validation(registry: dict, schema: dict) -> None:
    assert vr.check_schema(registry, schema) == []
    assert vr.check_consistency(registry) == []
    assert vr.check_architecture_inputs(registry) == []


def test_baseline_is_v1_and_candidates_are_deferred(registry: dict) -> None:
    for r in registry["baseline_requirements"]:
        assert r["version"] == "V1"
        assert "deferred_to_round" not in r
    for r in registry["candidate_requirements"]:
        assert r["deferred_to_round"] == "V2"


def test_ids_use_semantic_prefixes(registry: dict) -> None:
    for r in registry["baseline_requirements"]:
        assert r["id"].startswith("REQ-ADS-"), f"{r['id']} 缺少 REQ-ADS- 前缀"


def test_legacy_ids_are_complete_and_unique(registry: dict) -> None:
    lmap = registry["legacy_id_map"]
    assert len(lmap) == 39
    assert len(set(lmap.values())) == 39
    assert lmap["REQ-006"] == "REQ-ADS-NFR-SAFETY-001"


def test_every_asr_requirement_points_at_a_register_entry(registry: dict) -> None:
    for r in registry["baseline_requirements"]:
        if r["asr"]:
            assert r.get("asr_id"), f"{r['id']} 声明为 ASR 但无 asr_id"


# ---- 反向（Schema 层）----

def _schema_errors(reg: dict, schema: dict) -> list[str]:
    return vr.check_schema(reg, schema)


def test_missing_required_field_rejected(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    del bad["baseline_requirements"][0]["statement"]
    assert _schema_errors(bad, schema)


def test_invalid_type_rejected(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["baseline_requirements"][0]["type"] = "nice_to_have"
    assert _schema_errors(bad, schema)


def test_invalid_priority_rejected(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["baseline_requirements"][0]["priority"] = "high"
    assert _schema_errors(bad, schema)


def test_invariant_without_fallback_rejected(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    inv = next(r for r in bad["baseline_requirements"] if r["type"] == "invariant")
    del inv["fallback"]
    assert _schema_errors(bad, schema)


def test_invariant_with_non_must_priority_rejected(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    inv = next(r for r in bad["baseline_requirements"] if r["type"] == "invariant")
    inv["priority"] = "should"
    assert _schema_errors(bad, schema)


def test_non_functional_without_metric_rejected(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    nfr = next(
        r for r in bad["baseline_requirements"] if r["type"] in {"quality", "performance", "cost"}
    )
    del nfr["metric"]
    assert _schema_errors(bad, schema)


def test_baseline_asr_without_asr_id_rejected(registry: dict, schema: dict) -> None:
    """基线 ASR 必须指回 ASR 登记册；候选（有 deferred_to_round）豁免。"""
    bad = copy.deepcopy(registry)
    asr = next(r for r in bad["baseline_requirements"] if r["asr"])
    del asr["asr_id"]
    assert _schema_errors(bad, schema)


def test_deferred_asr_may_omit_asr_id(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    cand = next(r for r in bad["candidate_requirements"] if r["asr"])
    assert "asr_id" not in cand
    assert _schema_errors(bad, schema) == []


def test_missing_evolution_rounds_rejected(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    del bad["evolution_rounds"]
    assert _schema_errors(bad, schema)


def test_unknown_verification_method_rejected(registry: dict, schema: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["baseline_requirements"][0]["verification"] = ["vibes"]
    assert _schema_errors(bad, schema)


def test_flat_enforced_by_is_required(registry: dict, schema: dict) -> None:
    """课程格式要求扁平 enforced_by（note 行 1000）。"""
    bad = copy.deepcopy(registry)
    del bad["baseline_requirements"][0]["enforced_by"]
    assert _schema_errors(bad, schema)


# ---- 反向（一致性层）----

def _consistency_errors(reg: dict) -> list[str]:
    return vr.check_consistency(reg)


def test_duplicate_requirement_id_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["baseline_requirements"].append(copy.deepcopy(bad["baseline_requirements"][0]))
    assert any("重复" in e for e in _consistency_errors(bad))


def test_prefix_type_mismatch_rejected(registry: dict) -> None:
    """语义化 ID 的类别前缀必须与 type 相容。"""
    bad = copy.deepcopy(registry)
    bad["baseline_requirements"][0]["id"] = "REQ-ADS-NFR-SAFETY-099"
    assert any("不相容" in e for e in _consistency_errors(bad))


def test_undeclared_source_reference_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["baseline_requirements"][0]["source_refs"] = [{"source": "ghost_doc", "locator": "§1"}]
    assert any("未声明" in e for e in _consistency_errors(bad))


def test_unused_declared_source_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["sources"].append(
        {"key": "orphan", "path": "docs/none.md", "kind": "analysis", "authority": "informative"}
    )
    assert any("orphan" in e for e in _consistency_errors(bad))


def test_fix_the_bug_fallback_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    inv = next(r for r in bad["baseline_requirements"] if r["type"] == "invariant")
    inv["fallback"] = "fix the bug"
    assert any("fallback" in e for e in _consistency_errors(bad))


def test_retry_fallback_flagged(registry: dict) -> None:
    """课程行 1713：retry 是 fail-open，必须显式说明而非默默使用。"""
    bad = copy.deepcopy(registry)
    inv = next(r for r in bad["baseline_requirements"] if r["type"] == "invariant")
    inv["fallback"] = "重试或修复"
    assert any("fail-closed" in e for e in _consistency_errors(bad))


def test_open_question_referencing_unknown_requirement_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["open_questions"][0]["blocks"] = ["REQ-ADS-FR-999"]
    assert any("999" in e for e in _consistency_errors(bad))


def test_legacy_map_pointing_nowhere_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["legacy_id_map"]["REQ-001"] = "REQ-ADS-FR-999"
    assert any("REQ-ADS-FR-999" in e for e in _consistency_errors(bad))


def test_status_verified_without_automated_check_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["baseline_requirements"][0]["status"] = "verified"
    bad["baseline_requirements"][0]["verification"] = ["code_review"]
    assert any("verified" in e for e in _consistency_errors(bad))


def test_baseline_version_mismatch_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    bad["baseline_requirements"][0]["version"] = "V2"
    assert any("baseline_version" in e for e in _consistency_errors(bad))


# ---- 反向（架构输入层）----

def test_unknown_asr_id_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    asr = next(r for r in bad["baseline_requirements"] if r["asr"])
    asr["asr_id"] = "ASR-ADS-999"
    assert any("ASR-ADS-999" in e for e in vr.check_architecture_inputs(bad))


def test_unknown_invariant_id_rejected(registry: dict) -> None:
    bad = copy.deepcopy(registry)
    req = next(r for r in bad["baseline_requirements"] if r.get("invariants"))
    req["invariants"] = ["INV-ADS-999"]
    assert any("INV-ADS-999" in e for e in vr.check_architecture_inputs(bad))


def test_orphan_asr_rejected(registry: dict) -> None:
    """登记册里存在但无人引用的 ASR 必须被报出。"""
    bad = copy.deepcopy(registry)
    for r in bad["baseline_requirements"]:
        if r.get("asr_id") == "ASR-ADS-15":
            r["asr"] = False
            del r["asr_id"]
    assert any("ASR-ADS-15" in e for e in vr.check_architecture_inputs(bad))


# ---- 出口码契约 ----

def test_main_exit_codes() -> None:
    assert vr.main(["prog", str(vr.REGISTRY_PATH), str(vr.SCHEMA_PATH)]) == 0
