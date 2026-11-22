"""Mutation harness regressions for INV-ADS-011 and INV-V2-001 through INV-V2-012.

REQ-ADS-NFR-QA-002 / REQ-ADS-GOV-003: Negative tests prevent setup, import,
payload-signature and stale/mismatched evidence from masquerading as kills.
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import mutation_check as mc


def _failure(*, mutation="MUT-X", phase="call", exception="AssertionError", message="assert False"):
    return "[mutation-failure] " + json.dumps({"mutation": mutation, "nodeid": "test/offline/test_x.py::test_contract",
                                              "phase": phase, "exception": exception, "message": message})


def _output(**changes):
    return "[mutation] 已注入 MUT-X → module:method\n" + _failure(**changes)


def test_all_thirteen_original_and_twelve_v2_semantic_mutations_are_retained():
    expected_v1 = {f"INV-ADS-{n:03}" for n in [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16]}
    expected_v2 = {f"INV-V2-{n:03}" for n in range(1, 13)}
    expected_v3 = {f"INV-V3-{n:03}" for n in range(1, 9)}
    assert {m.invariant for m in mc.MUTATIONS} == expected_v1 | expected_v2 | expected_v3
    assert set(mc._declared_invariants()) == expected_v1 | expected_v2 | expected_v3


@pytest.mark.parametrize("phase", ["setup", "teardown"])
def test_non_call_failures_cannot_count_as_kills(phase):
    detected, note = mc._classify(1, _output(phase=phase))
    assert not detected
    assert "setup/teardown" in note


@pytest.mark.parametrize("kind", ["TypeError", "ValueError", "NameError", "ImportError", "ModuleNotFoundError"])
def test_payload_and_import_errors_are_not_behavioral_detection(kind):
    detected, note = mc._classify(1, _output(exception=kind, message="broken harness"))
    assert not detected
    assert note


@pytest.mark.parametrize("code", [0, 2, 3, 4, 5])
def test_only_normal_pytest_failure_exit_can_be_a_kill(code):
    assert not mc._classify(code, _output())[0]


def test_injection_followed_by_old_internal_import_error_is_not_a_kill():
    old_output = "[mutation] 已注入 MUT-X\nINTERNALERROR> ModuleNotFoundError: No module named eval_runner"
    assert not mc._classify(3, old_output)[0]
    assert not mc._classify(1, old_output)[0]


def test_failure_requires_structured_phase_evidence_and_matching_mutation():
    assert not mc._classify(1, "[mutation] 已注入 MUT-X\n1 failed")[0]
    assert not mc._classify(1, _output(mutation="MUT-STALE"))[0]
    assert not mc._classify(1, _output() + "\n[mutation] 已注入 MUT-OTHER")[0]


def test_assertion_and_expected_exception_guard_failures_are_real_detection():
    assert mc._classify(1, _output()) == (True, "")
    assert mc._classify(1, _output(exception="Failed", message="DID NOT RAISE ValueError")) == (True, "")
    assert not mc._classify(1, _output(exception="Failed", message="fixture malfunction"))[0]


def test_intentional_public_contract_escape_is_narrowly_identified():
    name = "MUT-RAISE-INSTEAD-OF-DEGRADE"
    record = _failure(mutation=name, exception="RuntimeError", message="mutated: 不再降级，直接抛异常")
    assert mc._classify(1, f"[mutation] 已注入 {name}\n" + record)[0]
    assert not mc._classify(1, _output(exception="RuntimeError", message="arbitrary bug"))[0]


def test_baseline_failure_prevents_injection_and_cannot_be_a_kill(monkeypatch):
    calls = []
    monkeypatch.setenv("MUTATION_ID", "STALE-PARENT-MUTANT")

    def run(command, **kwargs):
        calls.append((command, dict(kwargs["env"])))
        return SimpleNamespace(returncode=1, stdout="unmutated target already fails", stderr="")

    monkeypatch.setattr(mc.subprocess, "run", run)
    result = mc.run_mutation(mc.MUTATIONS[0], python=sys.executable, plugin_path=Path(mc.__file__))
    assert not result.detected
    assert len(calls) == 1
    assert "MUTATION_ID" not in calls[0][1]
    assert str(ROOT / "eval") in calls[0][1]["PYTHONPATH"].split(os.pathsep)
    assert "基线" in result.note


def test_baseline_and_mutant_run_identical_test_nodes_with_fresh_environment(monkeypatch):
    mutation = next(m for m in mc.MUTATIONS if m.invariant == "INV-V2-012")
    calls = []

    def run(command, **kwargs):
        calls.append((list(command), dict(kwargs["env"])))
        if len(calls) == 1:
            return SimpleNamespace(returncode=0, stdout="1 passed", stderr="")
        evidence = f"[mutation] 已注入 {mutation.mutation_id}\n" + _failure(mutation=mutation.mutation_id)
        return SimpleNamespace(returncode=1, stdout=evidence, stderr="")

    monkeypatch.setattr(mc.subprocess, "run", run)
    result = mc.run_mutation(mutation, python=sys.executable, plugin_path=Path(mc.__file__))
    assert result.detected
    assert calls[0][0] == calls[1][0]
    assert "MUTATION_ID" not in calls[0][1]
    assert calls[1][1]["MUTATION_ID"] == mutation.mutation_id
    assert list(mutation.tests) == calls[1][0][-len(mutation.tests):]


def test_no_valid_assertion_can_hide_an_unrelated_setup_or_signature_error():
    assert not mc._classify(1, _output() + "\n" + _failure(phase="setup"))[0]
    assert not mc._classify(1, _output() + "\n" + _failure(exception="TypeError"))[0]
