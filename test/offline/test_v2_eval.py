"""Replay-harness self-tests, ADR-003 D6 / ADR-005 and REQ-ADS-NFR-QA-004/GOV-003.

These are verification-tool tests. Product correctness has separate independent
TEST ownership; expectations here are fixed specification assets, not snapshots
copied from actual pipeline responses. Negative tests prove the gate can fail.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from urllib import request

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval import v2_runner


def _asset() -> dict:
    return json.loads(v2_runner.DEFAULT_CASES.read_text(encoding="utf-8"))


def _replace_case_text(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """Stub the case-file boundary; keep config/data/pipeline I/O real."""
    original_open = Path.open

    def case_open(path: Path, *args: object, **kwargs: object):
        if path == v2_runner.DEFAULT_CASES:
            return io.StringIO(text)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", case_open)


@pytest.fixture(scope="module")
def replay() -> dict:
    return v2_runner.run_eval()


def test_current_fixed_replay_passes(replay: dict) -> None:
    """REQ-ADS-NFR-QA-004: >=10 real V2 replays pass fixed money and refusal expectations."""
    assert replay["passed"], replay["violations"]
    assert replay["case_count"] >= 10
    assert replay["positive_count"] > 0 and replay["negative_count"] > 0
    assert replay["positive_count"] + replay["negative_count"] == replay["case_count"]
    assert replay["positive_pass_rate"] == 1
    assert replay["negative_matches"] == replay["negative_count"]
    assert replay["compliance_escape_count"] == 0
    assert replay["violations"] == []


def test_replay_evidence_contains_actual_outputs_and_atomic_balances(replay: dict) -> None:
    """INV-V2-002/011: actual responses, expected results, balances and canonical audits are retained."""
    for case in replay["cases"]:
        assert {"input", "expected", "actual", "balances", "audits", "matched", "violations"} <= case.keys()
        assert case["matched"] and case["actual"]
        for ad_id, state in case["balances"].items():
            assert type(state["spent_cents"]) is int
            assert 0 <= state["spent_cents"] <= state["total_cents"]
            assert state["remaining_cents"] == state["total_cents"] - state["spent_cents"]
            assert state["spent_cents"] == sum(
                record["settlement"]["charge_cents"]
                for record in case["audits"] if record["settlement"]["ad_id"] == ad_id
            )
    json.dumps(replay, allow_nan=False)


def test_idempotency_and_fault_cases_record_distinct_outcomes(replay: dict) -> None:
    """INV-V2-004/010: retries preserve the full response; unknown transactions show observed rollback."""
    cases = {case["id"]: case for case in replay["cases"]}
    retry = cases["V2-004-idempotent"]
    assert retry["actual"][0] == retry["actual"][1]
    assert len(retry["audits"]) == 1
    assert retry["steps"][1]["provider_calls"] == 1
    for case in replay["cases"]:
        if case["input"].get("fault_stage"):
            assert case["actual"][-1]["kind"] == "status_unknown"
            assert case["actual"][-1]["retry_same_request"] is True
            assert case["balances"] == case["initial_balances"]
            assert case["audits"] == []


def test_no_api_and_offline_latency_disclosure(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-ADS-NFR-QA-003/004: offline replay needs no credentials and makes no live-quality claim."""
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("offline replay attempted network access")

    monkeypatch.delenv("V2_LLM_API_KEY", raising=False)
    monkeypatch.setattr(request, "urlopen", reject_network)
    report = v2_runner.run_eval()
    assert report["passed"], report["violations"]
    assert report["provider"] == "fixed_offline"
    assert report["live_provider_tested"] is False
    assert "not real model performance" in report["latency_scope"]
    assert report["latency_sample_count"] >= report["case_count"]
    assert report["latency_p95_sec"] >= 0


@pytest.mark.parametrize("broken", ["not JSON", "{}", "[]", '{"version":NaN}', '{"version":1,"version":2}'])
def test_invalid_case_files_fail_closed(monkeypatch: pytest.MonkeyPatch, broken: str) -> None:
    """REQ-ADS-GOV-003/INV-V2-012 negative test: invalid verification assets never pass."""
    _replace_case_text(monkeypatch, broken)
    report = v2_runner.run_eval()
    assert report["passed"] is False
    assert report["violations"]


def test_missing_case_file_fails_closed() -> None:
    """REQ-ADS-NFR-QA-004 negative test: absent evidence cannot pass the replay gate."""
    report = v2_runner.run_eval(ROOT / "eval" / "this-v2-case-file-does-not-exist.json")
    assert report["passed"] is False
    assert report["case_count"] == 0
    assert report["violations"]


@pytest.mark.parametrize("mutation", ["too_few", "no_negative", "duplicate_id", "bad_anchor", "empty_steps", "unknown_provider", "bool_expected_money", "unknown_field"])
def test_malformed_fixture_contract_is_rejected(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """REQ-ADS-GOV-003/INV-V2-012 negative test: fixture contract defects cannot erase obligations."""
    asset = _asset()
    first = asset["cases"][0]
    if mutation == "too_few":
        asset["cases"] = asset["cases"][:9]
    elif mutation == "no_negative":
        for case in asset["cases"]:
            case["label"] = "MUST_PASS"
    elif mutation == "duplicate_id":
        asset["cases"][1]["id"] = first["id"]
    elif mutation == "bad_anchor":
        first["anchors"] = ["looks-good"]
    elif mutation == "empty_steps":
        first["steps"] = []
    elif mutation == "unknown_provider":
        first["input"]["provider"] = {"kind": "http"}
    elif mutation == "bool_expected_money":
        first["steps"][0]["expected"]["balances"]["ad_001"]["spent_cents"] = True
    else:
        first["steps"][0]["expected"]["ignored_assertion"] = "must not be silently ignored"
    _replace_case_text(monkeypatch, json.dumps(asset))
    report = v2_runner.run_eval()
    assert report["passed"] is False
    assert report["violations"]


def test_wrong_negative_reason_blocks_even_with_zero_positive_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-V2-012/GOV-003 negative test: MUST_FAIL mismatches independently block permissive quality rates."""
    asset = _asset()
    negative = next(case for case in asset["cases"] if case["id"] == "V2-008-malformed")
    negative["steps"][0]["expected"]["result"]["reason_code"] = "no_candidates"
    _replace_case_text(monkeypatch, json.dumps(asset))
    thresholds = deepcopy(v2_runner._thresholds())
    thresholds["pass_rate_threshold"] = 0
    monkeypatch.setattr(v2_runner, "_thresholds", lambda: thresholds)
    report = v2_runner.run_eval()
    assert report["positive_pass_rate"] == 1
    assert report["passed"] is False
    assert report["negative_matches"] == report["negative_count"] - 1
    assert any(violation.get("case_id") == negative["id"] for violation in report["violations"])


def test_audit_reconciliation_catches_overspend_and_unrecorded_debit(replay: dict) -> None:
    """INV-V2-002/004/011 negative test: canonical-audit reconciliation rejects unsafe money observations."""
    case = next(case for case in replay["cases"] if case["id"] == "V2-001-product-price")
    balances = deepcopy(case["balances"])
    balances["ad_001"]["spent_cents"] = balances["ad_001"]["total_cents"] + 1
    assert v2_runner._audit_violations(balances, case["audits"], case["actual"])
    assert v2_runner._audit_violations(case["balances"], [], case["actual"])
    audits = deepcopy(case["audits"])
    audits[0]["settlement"]["charge_cents"] = 1
    assert v2_runner._audit_violations(case["balances"], audits, case["actual"])


def test_cli_wrong_expectation_produces_nonzero_exit() -> None:
    """REQ-ADS-GOV-003 negative test: a deliberately false specification makes the real CLI exit 1."""
    asset = _asset()
    asset["cases"][0]["steps"][0]["expected"]["result"]["auction"]["price_cents"] = 119
    # Exercise the actual __main__ in a child process. Stub only the fixture-file
    # read because this repository's restricted Windows sandbox forbids temp-file I/O.
    script = """
import io
import runpy
import sys
from pathlib import Path
payload = sys.stdin.read()
original = Path.open
def fixture_open(path, *args, **kwargs):
    if path.name == 'v2_cases.json':
        return io.StringIO(payload)
    return original(path, *args, **kwargs)
Path.open = fixture_open
sys.argv = ['v2_runner.py', '--json', '--no-write']
runpy.run_path('eval/v2_runner.py', run_name='__main__')
"""
    process = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", script], input=json.dumps(asset),
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
    )
    assert process.returncode == 1, process.stderr
    report = json.loads(process.stdout)
    assert report["passed"] is False
    assert any(violation.get("case_id") == "V2-001-product-price" for violation in report["violations"])


def test_cli_json_output_and_no_write_modes() -> None:
    """REQ-ADS-NFR-QA-004: the executable CLI emits actual JSON replay evidence without files."""
    process = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "eval" / "v2_runner.py"), "--json", "--no-write"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
    )
    assert process.returncode == 0, process.stderr or process.stdout
    assert json.loads(process.stdout)["passed"] is True


def test_cli_optional_output_is_exact(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-ADS-NFR-QA-004: optional export matches stdout; stub only the file-write boundary."""
    written: dict[Path, str] = {}

    def capture(path: Path, content: str, **_kwargs: object) -> int:
        written[path] = content
        return len(content)

    monkeypatch.setattr(Path, "write_text", capture)
    destination = ROOT / "eval" / "optional-v2-report.json"
    assert v2_runner.main(["--json", "--output", str(destination)]) == 0
    assert json.loads(capsys.readouterr().out) == json.loads(written[destination])


def test_thresholds_are_loaded_from_config(replay: dict) -> None:
    """REQ-ADS-GOV-003: declared quality, escape and latency gates come from config-v2.yaml."""
    import yaml

    configuration = yaml.safe_load((ROOT / "config-v2.yaml").read_text(encoding="utf-8"))
    assert replay["thresholds"] == configuration["replay"]
