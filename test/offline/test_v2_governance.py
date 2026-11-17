"""V2 governance regressions exercise actual blockers, not approval claims.

REQ-ADS-FR-006, REQ-ADS-GOV-003, REQ-ADS-NFR-QA-003,
REQ-ADS-NFR-QA-004; INV-V2-008, INV-V2-012; INV-ADS-016.
Negative tests must fail for unknown policies, false safety results and proxy approvals.
"""

import ast
import io
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT / "src", ROOT / "scripts", ROOT / "eval"):
    sys.path.insert(0, str(folder))

import check_semantic_eval as semantic
import check_test_approval as approval
import fitness_functions as fitness
import validate_requirements as requirements
from eval_runner import CaseOutcome, EvalCase, ReplayReport

from app.cli_v2 import load_v2_config


def _registry():
    return yaml.safe_load((ROOT / "docs/req/requirements.yaml").read_text(encoding="utf-8"))


def test_effective_baseline_preserves_v1_and_activates_all_nineteen_v2_ids():
    registry = _registry()
    assert len([r for r in registry["baseline_requirements"] if r["version"] == "V1"]) == 22
    assert len([r for r in registry["baseline_requirements"] if r["version"] == "V2"]) == 19
    assert registry["project"]["baseline_versions"] == ["V1", "V2", "V3"]
    assert not registry["candidate_requirements"]
    assert not requirements.check_consistency(registry)


def test_version_policy_still_rejects_undeclared_or_missing_versions():
    registry = _registry()
    registry["baseline_requirements"][0]["version"] = "V99"
    assert requirements.check_consistency(registry)
    registry = _registry()
    registry["project"]["baseline_versions"] = ["V2"]
    assert requirements.check_consistency(registry)
    registry = _registry()
    registry["project"]["baseline_versions"].append("V99")
    assert requirements.check_consistency(registry)


@pytest.mark.parametrize("field,value", [
    ("score_formula", "__import__('os').system('unsafe')"),
    ("score_formula", "relevance + bid"),
    ("pricing", "second_price"),
    ("tie_break", "random"),
])
def test_formula_configuration_rejects_executable_or_unknown_policy(monkeypatch, field, value):
    config = yaml.safe_load((ROOT / "config-v2.yaml").read_text(encoding="utf-8"))
    config["policy"][field] = value
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: io.StringIO(yaml.safe_dump(config)))
    with pytest.raises(ValueError, match="unsupported auction policy"):
        load_v2_config("config-v2.yaml")


def test_semantic_gate_tracks_real_prompt_and_auction_paths():
    paths = ["src/selector/relevance.py", "src/bidding/engine.py", "src/bidding/ledger.py",
             "src/app/pipeline_v2.py", "data/bids-v2.json", "config-v2.yaml", "src/selector/context.py"]
    assert semantic.semantic_changes(paths + ["docs/readme.md"]) == sorted(paths)


def test_semantic_gate_runs_both_suites_and_blocks_failure(monkeypatch):
    calls = []

    def run(argv, **_kwargs):
        calls.append(argv)
        class Result:
            returncode = 1 if "v2_runner.py" in argv[1] else 0
            stdout = "fixed replay"
            stderr = "safety failure"
        return Result()

    monkeypatch.setattr(semantic.subprocess, "run", run)
    monkeypatch.setattr(Path, "is_file", lambda _path: True)
    assert semantic.threshold_check()
    assert [Path(args[1]).name for args in calls] == ["eval_runner.py", "v2_runner.py"]


def test_missing_eval_asset_blocks_instead_of_skipping(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _path: False)
    assert len(semantic.threshold_check()) == 2


def test_v1_must_fail_mismatch_blocks_even_when_quality_is_perfect():
    positive = EvalCase("positive", {}, "ad", "MUST_PASS", "regression", ("INV-ADS-016",))
    safety = EvalCase("safety", {}, "no_ad", "MUST_FAIL", "negative test", ("INV-ADS-016",))
    report = ReplayReport([CaseOutcome(positive, True), CaseOutcome(safety, False)])
    assert report.pass_rate == 1.0
    assert not report.passed
    report.outcomes[1].matched = True
    assert report.passed


def test_code_only_change_requires_requirement_specific_approved_tests():
    required, errors = approval.required_test_requirements(["src/bidding/engine.py"])
    assert not errors
    assert "REQ-ADS-FR-005" in {rid for ids in required.values() for rid in ids}
    assert "test/offline/test_bidding_v2.py" in required
    approvals = yaml.safe_load(approval.APPROVALS.read_text(encoding="utf-8"))["approvals"]
    covered = {rid for a in approvals if approval.is_effective(a) for rid in a["req_ids"]}
    assert "REQ-ADS-FR-005" not in covered


def test_unmapped_implementation_cannot_escape_approval():
    _required, errors = approval.required_test_requirements(["src/unknown/module.py"])
    assert errors


def test_proxy_or_unspecified_actor_cannot_create_human_approval():
    record = {"id": "TA-9999", "status": "approved", "approved_by": "Supervisor"}
    assert not approval.is_effective(record)
    record["actor_kind"] = "ai_proxy"
    assert not approval.is_effective(record)
    record["actor_kind"] = "human"
    assert approval.is_effective(record)
    record["approved_by"] = "AI proxy agent"
    assert not approval.is_effective(record)
    assert approval.parse_iso("2026-10-31T10:00:00") is None


def test_v2_fixed_evaluation_has_safety_and_budget_cases():
    data = json.loads((ROOT / "eval/v2_cases.json").read_text(encoding="utf-8"))
    cases = data if isinstance(data, list) else data["cases"]
    assert len(cases) >= 10
    text = json.dumps(cases).lower()
    assert "budget" in text or "exhaust" in text
    assert "tie" in text
    assert "invalid" in text or "nonfinite" in text or "nan" in text


def test_bidding_core_has_no_model_or_network_dependency():
    forbidden = {"selector", "openai", "requests", "urllib", "http"}
    files = list((ROOT / "src/bidding").glob("*.py"))
    assert files
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imports |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not imports & forbidden


def test_fitness_resolves_real_targets_and_rejects_trivial_evidence(monkeypatch):
    assert fitness.target_exists("bidding.ledger.Ledger.finalize")
    assert not fitness.target_exists("bidding.ledger.Ledger.missing_method")
    monkeypatch.setattr(Path, "is_file", lambda _path: True)
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: "def test_placeholder():\n    assert True\n")
    assert fitness.evidence_errors(["test_fake.py::test_placeholder"])


def test_all_v2_enforcement_and_exact_evidence_exist():
    report = fitness.Report()
    fitness.check_v2_contracts(report, _registry())
    assert not report.failures, report.failures


def test_untracked_and_working_files_are_not_ignored_by_gate(monkeypatch):
    outputs = {("diff", "--name-only", "base...HEAD"): "README.md\n",
               ("diff", "--name-only", "HEAD"): "config-v2.yaml\n",
               ("ls-files", "--others", "--exclude-standard"): "src/bidding/new.py\n"}
    monkeypatch.setattr(semantic, "git", lambda *args: outputs[args])
    assert semantic.changed_files("base", None) == ["README.md", "config-v2.yaml", "src/bidding/new.py"]


def test_approval_timing_uses_change_range_instead_of_historical_file_creation(monkeypatch):
    outputs = {("diff", "--name-only", "HEAD"): "",
               ("ls-files", "--others", "--exclude-standard"): "",
               ("log", "base..HEAD", "--format=%aI", "--", "src/bidding/engine.py"):
               "2026-10-31T12:00:00+00:00\n2026-10-30T12:00:00+00:00\n"}
    monkeypatch.setattr(approval, "git", lambda *args: outputs[args])
    stamp = approval.implementation_time(["src/bidding/engine.py"], [], "base")
    assert stamp.isoformat() == "2026-10-30T12:00:00+00:00"


def test_uncommitted_implementation_has_no_verifiable_approval_timestamp(monkeypatch):
    outputs = {("diff", "--name-only", "HEAD"): "src/bidding/engine.py\n",
               ("ls-files", "--others", "--exclude-standard"): ""}
    monkeypatch.setattr(approval, "git", lambda *args: outputs[args])
    assert approval.implementation_time(["src/bidding/engine.py"], [], "base") is None


def test_dependency_gate_rejects_undeclared_runtime_import(monkeypatch, capsys):
    import check_dependencies
    monkeypatch.setattr(check_dependencies, "imports_in", lambda *_args: {"undeclared_runtime_package"})
    assert check_dependencies.main() == 1
    assert "undeclared_runtime_package" in capsys.readouterr().out


def test_consistency_audit_checks_actual_enforcement_targets(capsys):
    import audit_implementation
    assert audit_implementation.main() == 0
    report = capsys.readouterr().out
    assert "REQ-ADS-GOV-003" in report
    assert "REQ-ADS-NFR-QA-004" in report


def test_demo_reconciles_observed_spend_and_idempotency():
    import demo_v2
    report = demo_v2.run_demo()
    assert report["scenario_count"] == 7
    assert report["main_audit_count"] == 3
    assert report["total_observed_spend_cents"] == 440
    assert report["total_observed_spend_cents"] == sum(b["spent_cents"] for b in report["main_budgets"].values())
    assert report["scenarios"][0]["result"] == report["scenarios"][1]["result"]
