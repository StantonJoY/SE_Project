"""Run the real V2 pipeline against fixed, independently specified replay cases.

Implements ADR-005 (atomic settlement), ADR-003 D6 (negative cases block),
REQ-ADS-NFR-QA-004/GOV-003 and INV-V2-002/004/010/011/012.
This is offline verification evidence, never evidence of live model quality.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ads.banned_words import BannedWords  # noqa: E402
from ads.repository import AdRepository  # noqa: E402
from app.pipeline_v2 import recommend_v2  # noqa: E402
from bidding import Ledger, validate_bids  # noqa: E402
from compliance.pipeline import run_compliance  # noqa: E402
from compliance.rules import SceneRules  # noqa: E402
from render.schema_v2 import validate_v2_result  # noqa: E402
from scene.parser import parse_scene  # noqa: E402
from selector.relevance import FixedRelevanceClient  # noqa: E402

DEFAULT_CASES = ROOT / "eval" / "v2_cases.json"
_INPUT_FIELDS = {
    "scene", "bids", "seed_bids", "bid_mode", "provider", "fault_stage",
    "context_budget_tokens", "policy_version",
}


class CaseError(ValueError):
    """A malformed verification asset cannot produce passing evidence."""


def _object(value: Any, required: set[str], allowed: set[str], name: str) -> dict:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - allowed:
        raise CaseError(f"{name}: missing/unknown fields or not an object")
    return value


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise CaseError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise CaseError(f"nonfinite JSON constant: {value}")


def _validate_input(value: Any, *, partial: bool = False) -> None:
    item = _object(value, set() if partial else {"scene", "bids", "provider"}, _INPUT_FIELDS, "input")
    if "bids" in item and (not isinstance(item["bids"], list) or not item["bids"]):
        raise CaseError("bids must be a nonempty array")
    if "seed_bids" in item and not isinstance(item["seed_bids"], list):
        raise CaseError("seed_bids must be an array")
    if item.get("bid_mode", "validated") not in {"validated", "raw"}:
        raise CaseError("unknown bid_mode")
    if item.get("fault_stage") not in {None, "after_debit", "before_audit", "before_commit"}:
        raise CaseError("unknown fault stage")
    if "provider" in item:
        provider = _object(item["provider"], {"kind"}, {"kind", "scores", "raw"}, "provider")
        kind = provider["kind"]
        if kind == "fixed":
            if set(provider) != {"kind", "scores"} or not isinstance(provider["scores"], dict):
                raise CaseError("fixed provider requires scores only")
        elif kind == "raw":
            if set(provider) != {"kind", "raw"} or not isinstance(provider["raw"], str):
                raise CaseError("raw provider requires JSON text only")
        elif kind in {"timeout", "error"}:
            if set(provider) != {"kind"}:
                raise CaseError("failure provider takes no arguments")
        else:
            raise CaseError("unknown/offline-only provider kind")


def _validate_expected(value: Any) -> None:
    expected = _object(value, {"result", "balances", "audit_count", "provider_calls"},
                       {"result", "balances", "audit_count", "provider_calls", "same_as_step"}, "expected")
    result = _object(expected["result"], {"kind"},
                     {"kind", "ad", "auction", "reason_code", "retry_same_request"}, "expected result")
    if result["kind"] == "ad":
        _object(result.get("ad"), {"ad_id"}, {"ad_id"}, "expected ad")
        auction = _object(result.get("auction"), {"price_cents", "score", "relevance"},
                          {"price_cents", "score", "relevance", "bid_cents",
                           "budget_before_cents", "budget_after_cents"}, "expected auction")
        if any(type(number) is not int or number < 0 for number in auction.values()):
            raise CaseError("expected auction requires nonnegative strict integers")
    elif result["kind"] == "no_ad":
        if not isinstance(result.get("reason_code"), str) or not result["reason_code"]:
            raise CaseError("expected no_ad requires a reason_code")
    elif result["kind"] == "status_unknown":
        if result.get("retry_same_request") is not True:
            raise CaseError("expected unknown status requires retry_same_request=true")
    else:
        raise CaseError("unknown expected result kind")
    for key in ("audit_count", "provider_calls"):
        if type(expected[key]) is not int or expected[key] < 0:
            raise CaseError(f"expected {key} must be a nonnegative integer")
    if "same_as_step" in expected and (type(expected["same_as_step"]) is not int or expected["same_as_step"] < 0):
        raise CaseError("same_as_step must be a nonnegative integer")
    if not isinstance(expected["balances"], dict) or not expected["balances"]:
        raise CaseError("expected balances must be a nonempty object")
    for state in expected["balances"].values():
        _object(state, {"spent_cents", "remaining_cents", "status"},
                {"spent_cents", "remaining_cents", "total_cents", "status"}, "expected balance")
        if state["status"] not in {"active", "paused", "exhausted"}:
            raise CaseError("unknown expected budget status")
        if any(type(number) is not int or number < 0 for key, number in state.items() if key != "status"):
            raise CaseError("expected money must be a nonnegative strict integer")


def _load_cases(path: str | Path) -> tuple[dict, list[dict]]:
    with Path(path).open(encoding="utf-8") as stream:
        payload = json.load(stream, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    # JSON number exponents can overflow to Infinity without parse_constant.
    json.dumps(payload, allow_nan=False)
    _object(payload, {"version", "basis", "defaults", "cases"},
            {"version", "basis", "defaults", "cases"}, "case file")
    if payload["version"] != "v2-fixed-replay-1" or not isinstance(payload["basis"], str) or not payload["basis"]:
        raise CaseError("missing specification basis or unsupported case version")
    defaults = payload["defaults"]
    _validate_input(defaults)
    cases = payload["cases"]
    if not isinstance(cases, list) or len(cases) < 10:
        raise CaseError("V2 replay requires at least ten fixed cases")
    seen: set[str] = set()
    labels: set[str] = set()
    for case in cases:
        _object(case, {"id", "label", "basis", "anchors", "input", "steps"},
                {"id", "label", "basis", "anchors", "input", "steps"}, "case")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise CaseError("case IDs must be nonempty and unique")
        seen.add(case_id)
        if case["label"] not in {"MUST_PASS", "MUST_FAIL"}:
            raise CaseError("unknown case label")
        labels.add(case["label"])
        if not isinstance(case["basis"], str) or not case["basis"]:
            raise CaseError("case lacks specification basis")
        anchors = case["anchors"]
        if not isinstance(anchors, list) or not anchors or any(
            not isinstance(anchor, str) or not re.fullmatch(r"(?:REQ-ADS-[A-Z-]+|INV-(?:ADS|V2))-\d{3}", anchor)
            for anchor in anchors
        ):
            raise CaseError("case anchors must reference semantic REQ/INV IDs")
        _validate_input(case["input"], partial=True)
        merged = defaults | case["input"]
        _validate_input(merged)
        if not isinstance(case["steps"], list) or not case["steps"]:
            raise CaseError("each case needs request steps")
        for index, step in enumerate(case["steps"]):
            _object(step, {"request_id", "input", "expected"}, {"request_id", "input", "expected"}, "step")
            if not isinstance(step["request_id"], str) or not step["request_id"].strip():
                raise CaseError("request_id must be nonempty")
            _validate_input(step["input"], partial=True)
            if step["input"].keys() - {"scene", "provider", "policy_version", "context_budget_tokens"}:
                raise CaseError("steps cannot reseed budgets or change transaction fault hooks")
            _validate_expected(step["expected"])
            if step["expected"].get("same_as_step", -1) >= index:
                raise CaseError("same_as_step must reference an earlier step")
        if case["label"] == "MUST_FAIL" and case["steps"][-1]["expected"]["result"]["kind"] == "ad":
            raise CaseError("MUST_FAIL must end with a rejected or unknown request")
    if labels != {"MUST_PASS", "MUST_FAIL"}:
        raise CaseError("both positive and negative cases are required")
    return defaults, cases


class _OfflineProvider:
    """Local advice/fault fixture; only the actual pipeline decides an outcome."""

    def __init__(self, specification: dict) -> None:
        self.specification = specification
        self.calls = 0
        self.candidates: list[list[str]] = []

    def score(self, scene: dict, candidates: list[dict]) -> str:
        self.calls += 1
        self.candidates.append([candidate["ad_id"] for candidate in candidates])
        kind = self.specification["kind"]
        if kind == "timeout":
            raise TimeoutError("offline injected timeout")
        if kind == "error":
            raise RuntimeError("offline injected provider failure")
        if kind == "raw":
            return self.specification["raw"]
        return FixedRelevanceClient(self.specification["scores"]).score(scene, candidates)


def _subset(expected: Any, actual: Any, path: str = "result") -> list[str]:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object"]
        return [message for key, value in expected.items()
                for message in _subset(value, actual.get(key), f"{path}.{key}")]
    if type(expected) is not type(actual) or expected != actual:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []


def _audit_violations(balances: dict, audits: list[dict], results: list[dict]) -> list[str]:
    """Independently reconcile all money with canonical committed evidence."""
    violations: list[str] = []
    charges = dict.fromkeys(balances, 0)
    seen: set[str] = set()
    seen_audits: set[str] = set()
    for record in audits:
        request_id = record.get("request_id")
        if request_id in seen:
            violations.append("duplicate canonical request audit")
        seen.add(request_id)
        if record.get("audit_id") in seen_audits:
            violations.append("duplicate canonical audit identity")
        seen_audits.add(record.get("audit_id"))
        final, evidence, settlement = record.get("final", {}), record.get("evidence", {}), record.get("settlement", {})
        if not record.get("audit_id") or final.get("audit_id") != record.get("audit_id") or final.get("request_id") != request_id:
            violations.append("canonical audit identity differs from saved response")
        charge = settlement.get("charge_cents")
        if type(charge) is not int or charge < 0:
            violations.append("canonical charge is not nonnegative integer cents")
            continue
        if final.get("kind") == "ad":
            ad_id = final.get("ad", {}).get("ad_id")
            auction = final.get("auction", {})
            if ad_id not in charges or settlement.get("ad_id") != ad_id:
                violations.append("canonical charge names an unknown/different ad")
                continue
            if charge != auction.get("price_cents") or charge != auction.get("bid_cents"):
                violations.append("canonical charge differs from pay-as-bid price")
            before, after = settlement.get("budget_before_cents"), settlement.get("budget_after_cents")
            if type(before) is not int or type(after) is not int or before - charge != after or after < 0:
                violations.append("canonical budget debit arithmetic differs")
            if before != auction.get("budget_before_cents") or after != auction.get("budget_after_cents"):
                violations.append("saved response differs from canonical budget snapshots")
            if before != balances[ad_id].get("total_cents", 0) - charges[ad_id]:
                violations.append("canonical budget history does not form a continuous debit sequence")
            charges[ad_id] += charge
            compliance = evidence.get("compliance", {})
            if compliance.get("approved") is not True or compliance.get("executed") is not True:
                violations.append("charged ad lacks approved deterministic compliance evidence")
            if not {"scene", "bids", "budgets", "scores", "candidate_ids", "provenance", "auction_choice"} <= evidence.keys():
                violations.append("charged ad lacks complete auction replay evidence")
        elif final.get("kind") != "no_ad" or charge != 0 or settlement.get("ad_id") is not None:
            violations.append("non-ad canonical decision has a charge or invalid outcome")
    for ad_id, state in balances.items():
        total, spent, remaining = (state.get(key) for key in ("total_cents", "spent_cents", "remaining_cents"))
        if any(type(value) is not int for value in (total, spent, remaining)):
            violations.append(f"{ad_id}: money is not integer cents")
            continue
        if not 0 <= spent <= total or remaining != total - spent:
            violations.append(f"{ad_id}: overspend or inconsistent remaining budget")
        if spent != charges[ad_id]:
            violations.append(f"{ad_id}: spent differs from sum of canonical charges")
    by_request = {record.get("request_id"): record for record in audits}
    for result in results:
        if result.get("kind") == "status_unknown" or result.get("reason_code") in {"request_conflict", "request_invalid"}:
            continue
        if by_request.get(result.get("request_id"), {}).get("final") != result:
            violations.append("finalized response has no identical canonical audit")
    return violations


def _run_case(case: dict, defaults: dict, repo: AdRepository,
              banned: BannedWords, rules: SceneRules) -> tuple[dict, list[float], int]:
    inputs = deepcopy(defaults | case["input"])
    known_ids = {ad.ad_id for ad in repo.all()}
    seeded = validate_bids(inputs.get("seed_bids", inputs["bids"]), known_ad_ids=known_ids)
    bids = ({record["ad_id"]: record for record in inputs["bids"]} if inputs.get("bid_mode") == "raw"
            else validate_bids(inputs["bids"], known_ad_ids=known_ids))

    def fault(stage: str) -> None:
        if stage == inputs.get("fault_stage"):
            raise OSError(f"offline transaction failure at {stage}")

    violations: list[str] = []
    results: list[dict] = []
    steps: list[dict] = []
    latencies: list[float] = []
    escapes = 0
    provider_calls = 0
    with Ledger(":memory:", fault_hook=fault) as ledger:
        ledger.seed(seeded)
        initial_balances = ledger.budgets()
        for step_index, step in enumerate(case["steps"]):
            request_input = inputs | step["input"]
            provider = _OfflineProvider(request_input["provider"])
            start = time.perf_counter()
            result = recommend_v2(
                request_input["scene"], request_id=step["request_id"], repo=repo,
                bids=bids, client=provider, ledger=ledger, banned_words=banned, rules=rules,
                policy_version=request_input.get("policy_version", "pay-as-bid-v1"),
                context_budget_tokens=request_input.get("context_budget_tokens", 2000),
            )
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            results.append(result)
            provider_calls += provider.calls
            balances, audits = ledger.budgets(), ledger.audit_records()
            expected = step["expected"]
            issues = _subset(expected["result"], result)
            issues += [f"render: {error}" for error in validate_v2_result(result)]
            if set(balances) != set(expected["balances"]):
                issues.append("expected balance IDs differ from durable budget IDs")
            issues += _subset(expected["balances"], balances, "balances")
            if len(audits) != expected["audit_count"]:
                issues.append(f"audit count: expected {expected['audit_count']}, got {len(audits)}")
            if provider_calls != expected["provider_calls"]:
                issues.append(f"provider calls: expected {expected['provider_calls']}, got {provider_calls}")
            if "same_as_step" in expected and result != results[expected["same_as_step"]]:
                issues.append("idempotent response differs from its complete saved response")
            issues += _audit_violations(balances, audits, results)
            if result.get("kind") == "ad":
                chosen = repo.get(result.get("ad", {}).get("ad_id"))
                scene = parse_scene(request_input["scene"])
                candidates = repo.filter_by_scene(scene)
                if chosen is None or not run_compliance(chosen, scene, candidates, banned, rules).approved:
                    escapes += 1
                    issues.append("independent compliance replay rejected a displayed ad")
            violations.extend(f"step {step_index}: {issue}" for issue in issues)
            steps.append({"input": {"request_id": step["request_id"], **request_input},
                          "expected": expected, "actual": result, "balances": balances,
                          "audits": audits, "provider_calls": provider_calls,
                          "provider_candidate_ids": provider.candidates,
                          "latency_sec": elapsed, "matched": not issues, "violations": issues})
        report = {"id": case["id"], "label": case["label"], "basis": case["basis"],
                  "anchors": case["anchors"], "input": inputs,
                  "expected": [step["expected"] for step in case["steps"]],
                  "actual": results, "initial_balances": initial_balances,
                  "balances": ledger.budgets(), "audits": ledger.audit_records(),
                  "steps": steps, "matched": not violations, "violations": violations}
    return report, latencies, escapes


def _thresholds() -> dict:
    with (ROOT / "config-v2.yaml").open(encoding="utf-8") as stream:
        configuration = yaml.safe_load(stream)
    replay = _object(configuration.get("replay"),
                     {"pass_rate_threshold", "compliance_escape_limit", "latency_p95_threshold_sec"},
                     {"pass_rate_threshold", "compliance_escape_limit", "latency_p95_threshold_sec"}, "replay config")
    rate, escapes, latency = (replay[key] for key in
                              ("pass_rate_threshold", "compliance_escape_limit", "latency_p95_threshold_sec"))
    if type(rate) not in {int, float} or not math.isfinite(rate) or not 0 <= rate <= 1:
        raise CaseError("invalid pass-rate threshold")
    if type(escapes) is not int or escapes != 0:
        raise CaseError("compliance escape limit must stay zero")
    if type(latency) not in {int, float} or not math.isfinite(latency) or latency <= 0:
        raise CaseError("invalid latency threshold")
    return replay


def run_eval(cases_path: Path | str | None = None) -> dict:
    """REQ-ADS-NFR-QA-004/GOV-003: no negative mismatch can be hidden by averages."""
    report: dict = {"passed": False, "case_count": 0, "positive_count": 0, "negative_count": 0,
                    "violations": [], "cases": [], "provider": "fixed_offline",
                    "live_provider_tested": False,
                    "latency_scope": "local SQLite + offline advice; not real model performance",
                    "cases_path": str(cases_path or DEFAULT_CASES)}
    latencies: list[float] = []
    try:
        thresholds = _thresholds()
        report["thresholds"] = thresholds
        defaults, cases = _load_cases(cases_path or DEFAULT_CASES)
        report.update(case_count=len(cases),
                      positive_count=sum(case["label"] == "MUST_PASS" for case in cases),
                      negative_count=sum(case["label"] == "MUST_FAIL" for case in cases))
        repo = AdRepository.load(ROOT / "data" / "ads.json")
        banned = BannedWords.load(ROOT / "data" / "banned_words.json")
        rules = SceneRules.load(ROOT / "data" / "scene_rules.json")
        escapes = 0
        for case in cases:
            try:
                case_report, timings, case_escapes = _run_case(case, defaults, repo, banned, rules)
            except Exception as exc:  # noqa: BLE001 - a broken replay never counts as success
                case_report = {**case, "expected": [step["expected"] for step in case["steps"]],
                               "actual": [], "balances": {}, "audits": [], "matched": False,
                               "violations": [f"replay raised {type(exc).__name__}: {exc}"]}
                timings, case_escapes = [], 0
            report["cases"].append(case_report)
            latencies.extend(timings)
            escapes += case_escapes
            report["violations"].extend({"case_id": case["id"], "message": message}
                                        for message in case_report["violations"])
        positive_matches = sum(case["matched"] for case in report["cases"] if case["label"] == "MUST_PASS")
        negative_matches = sum(case["matched"] for case in report["cases"] if case["label"] == "MUST_FAIL")
        positive_rate = positive_matches / report["positive_count"]
        ordered = sorted(latencies)
        p95 = ordered[math.ceil(len(ordered) * 0.95) - 1] if ordered else None
        report.update(positive_pass_rate=positive_rate, positive_matches=positive_matches,
                      negative_matches=negative_matches, compliance_escape_count=escapes,
                      latency_sample_count=len(latencies), latency_p95_sec=p95)
        if positive_rate < thresholds["pass_rate_threshold"]:
            report["violations"].append({"message": "positive pass rate below configured threshold"})
        if escapes > thresholds["compliance_escape_limit"]:
            report["violations"].append({"message": "compliance escape limit exceeded"})
        if p95 is None or p95 > thresholds["latency_p95_threshold_sec"]:
            report["violations"].append({"message": "offline latency threshold exceeded or no timing samples"})
        report["passed"] = not report["violations"] and negative_matches == report["negative_count"]
    except Exception as exc:  # noqa: BLE001 - malformed/missing assets fail closed
        report["violations"].append({"message": f"evaluation setup failed: {type(exc).__name__}: {exc}"})
    report["violation_count"] = len(report["violations"])
    return report


def main(argv: list[str] | None = None) -> int:
    """Return an actual failing process status when replay evidence is unacceptable."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--json", action="store_true", help="print the full JSON report")
    output_options = parser.add_mutually_exclusive_group()
    output_options.add_argument("--output", type=Path, help="also save the full JSON report")
    output_options.add_argument("--no-write", action="store_true", help="print evidence without writing report files")
    args = parser.parse_args(argv)
    report = run_eval(args.cases)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        try:
            args.output.write_text(encoded + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Cannot save replay evidence: {exc}", file=sys.stderr)
            return 1
    if args.json:
        print(encoded)
    else:
        print(f"V2 offline replay: {'PASS' if report['passed'] else 'FAIL'}; "
              f"cases={report['case_count']} positive={report['positive_count']} "
              f"negative={report['negative_count']} violations={report['violation_count']}")
        print("Provider: fixed offline; live_provider_tested=false; latency is local replay only.")
        for violation in report["violations"]:
            print(f"  {violation.get('case_id', 'gate')}: {violation['message']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
