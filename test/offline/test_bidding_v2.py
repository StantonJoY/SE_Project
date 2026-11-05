"""Independent V2 bidding tests derived from requirements and public contracts.

REQ-ADS-NFR-SAFETY-006/007; REQ-ADS-ARCH-005/006/007/008/009/010/011;
REQ-ADS-FR-005/006/007/008; REQ-ADS-SEC-002; REQ-ADS-NFR-QA-003;
REQ-ADS-NFR-PERF-002. Negative tests exercise numeric and transaction boundaries.
Implementation source is deliberately not consulted by this TEST agent.
"""

import copy
import dataclasses
import os
import statistics
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from bidding import (
    Bid,
    BidError,
    InsufficientBudget,
    Ledger,
    LedgerError,
    RequestConflict,
    choose_winner,
    validate_bids,
)


def _record(ad_id="a", bid_cents=7, budget_cents=100, **overrides):
    return dict(ad_id=ad_id, bid_cents=bid_cents, budget_cents=budget_cents, **overrides)


def _bids(*records):
    return validate_bids(list(records))


def _budgets(bids):
    return {
        key: dict(
            total_cents=bid.budget_cents,
            spent_cents=0,
            remaining_cents=bid.budget_cents,
            status="exhausted" if bid.budget_cents == 0 else bid.status,
        )
        for key, bid in bids.items()
    }


def _no_ad(request_id):
    return {"kind": "no_ad", "request_id": request_id, "audit_id": f"aud-{request_id}", "reason_code": "test", "detail": "test"}


def _ad_result(request_id):
    return {"kind": "ad", "request_id": request_id, "audit_id": f"aud-{request_id}", "ad": {"ad_id": "a"}, "auction": {}}


def _commit(ledger, request_id, fingerprint=None):
    return ledger.finalize(
        request_id,
        fingerprint or request_id,
        _ad_result(request_id),
        {"case": "independent-ledger-test"},
        ad_id="a",
        charge_cents=7,
    )


@contextmanager
def _file_ledger_path():
    """Use an existing writable directory; sandbox-created subdirectories have unusable ACLs."""
    descriptor, filename = tempfile.mkstemp(prefix="v2-ledger-test-", suffix=".sqlite", dir=ROOT)
    os.close(descriptor)
    path = Path(filename)
    try:
        yield path
    finally:
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(str(path) + suffix).unlink(missing_ok=True)


@pytest.fixture
def ledger():
    instance = Ledger()
    try:
        yield instance
    finally:
        instance.close()


def test_bid_defaults_frozen_and_loading_is_non_mutating():
    """REQ-ADS-NFR-SAFETY-006, REQ-ADS-SEC-002: immutable validated bid contract."""
    records = [_record()]
    original = copy.deepcopy(records)
    bids = validate_bids(records, known_ad_ids={"a"})
    assert records == original
    assert bids == {"a": Bid("a", 7, 100)}
    assert bids["a"].bid_floor == 1
    assert bids["a"].bid_ceiling == 1_000_000
    assert bids["a"].status == "active"
    assert dataclasses.is_dataclass(bids["a"])
    with pytest.raises(dataclasses.FrozenInstanceError):
        bids["a"].bid_cents = 8


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.0, "7", None, float("nan"), float("inf"), -float("inf")])
def test_reject_invalid_bid_values(value):
    """REQ-ADS-NFR-SAFETY-006/007, REQ-ADS-ARCH-008: negative test rejects invalid money."""
    with pytest.raises(BidError):
        validate_bids([_record(bid_cents=value)])


@pytest.mark.parametrize("field,value", [
    ("budget_cents", True), ("budget_cents", -1), ("budget_cents", 2.5),
    ("budget_cents", float("inf")), ("budget_cents", "100"),
    ("bid_floor", True), ("bid_floor", 0), ("bid_floor", 1.5),
    ("bid_ceiling", True), ("bid_ceiling", 0), ("bid_ceiling", float("nan")),
])
def test_reject_invalid_budget_and_bound_types(field, value):
    """REQ-ADS-ARCH-008, REQ-ADS-SEC-002: negative test forbids coercing malformed cents."""
    record = _record()
    record[field] = value
    with pytest.raises(BidError):
        validate_bids([record])


@pytest.mark.parametrize("overrides", [
    {"bid_floor": 8}, {"bid_ceiling": 6}, {"bid_floor": 9, "bid_ceiling": 8},
    {"bid_cents": 1_000_001}, {"status": "ACTIVE"}, {"status": "other"},
    {"status": True}, {"price_cents": 1}, {"budget_spent": 10},
])
def test_reject_out_of_range_status_and_extra_fields(overrides):
    """REQ-ADS-NFR-SAFETY-006, REQ-ADS-SEC-002: negative test validates schema and ranges."""
    record = _record()
    record.update(overrides)
    with pytest.raises(BidError):
        validate_bids([record])


@pytest.mark.parametrize("missing", ["ad_id", "bid_cents", "budget_cents"])
def test_reject_missing_required_bid_fields(missing):
    """REQ-ADS-SEC-002: negative test requires complete bid records."""
    record = _record()
    del record[missing]
    with pytest.raises(BidError):
        validate_bids([record])


def test_loading_rejects_duplicate_and_unknown_ad_ids():
    """REQ-ADS-SEC-002: negative test prevents ambiguous or foreign bid identities."""
    with pytest.raises(BidError):
        validate_bids([_record(), _record()])
    with pytest.raises(BidError):
        validate_bids([_record()], known_ad_ids={"b"})
    for invalid_id in ("", None, True, 7):
        with pytest.raises(BidError):
            validate_bids([_record(ad_id=invalid_id)])


@pytest.mark.parametrize("amount", [1, 7, 1_000_000])
def test_bid_bounds_are_inclusive(amount):
    """REQ-ADS-NFR-SAFETY-006: exact lower and upper boundaries remain valid."""
    bids = validate_bids([_record(bid_cents=amount, bid_floor=amount, bid_ceiling=amount)])
    assert bids["a"].bid_cents == amount


def test_winner_is_product_of_relevance_and_bid_at_pay_as_bid_price():
    """REQ-ADS-FR-005/006, REQ-ADS-ARCH-010: score and price are code-owned integers."""
    bids = _bids(_record("a", 100), _record("b", 200, 1000))
    winner = choose_winner(bids, {"a": 90, "b": 50}, _budgets(bids))
    assert winner is not None
    assert (winner.ad_id, winner.bid_cents, winner.relevance, winner.score, winner.price_cents) == (
        "b", 200, 50, 10_000, 200,
    )
    assert all(type(value) is int for value in (winner.bid_cents, winner.relevance, winner.score, winner.price_cents))


def test_pure_deterministic_tie_break_does_not_depend_on_input_order():
    """REQ-ADS-ARCH-009/011: same score selects ascending ID without mutating inputs."""
    records = [_record("b", 20), _record("a", 10)]
    winners = []
    for ordered in (records, records[::-1], records):
        bids = _bids(*ordered)
        scores = {"b": 50, "a": 100}
        budgets = _budgets(bids)
        before = copy.deepcopy((bids, scores, budgets))
        for _ in range(5):
            winner = choose_winner(bids, scores, budgets)
            assert winner is not None
            winners.append((winner.ad_id, winner.score, winner.price_cents))
        assert (bids, scores, budgets) == before
    assert winners == [("a", 1000, 10)] * 15


@pytest.mark.parametrize("ineligibility", ["zero_relevance", "paused", "exhausted", "unaffordable", "zero_budget"])
def test_ineligible_high_bid_cannot_displace_affordable_candidate(ineligibility):
    """REQ-ADS-ARCH-006, REQ-ADS-FR-005/007: negative test excludes ineligible leaders."""
    bids = _bids(_record("a", 100), _record("b", 7))
    scores = {"a": 100, "b": 1}
    budgets = _budgets(bids)
    if ineligibility == "zero_relevance":
        scores["a"] = 0
    elif ineligibility == "paused":
        bids["a"] = Bid("a", 100, 100, status="paused")
        budgets["a"]["status"] = "paused"
    elif ineligibility == "exhausted":
        budgets["a"].update(spent_cents=100, remaining_cents=0, status="exhausted")
    elif ineligibility == "unaffordable":
        budgets["a"].update(spent_cents=1, remaining_cents=99)
    else:
        bids["a"] = Bid("a", 100, 0)
        budgets["a"] = dict(total_cents=0, spent_cents=0, remaining_cents=0, status="exhausted")
    winner = choose_winner(bids, scores, budgets)
    assert winner is not None and winner.ad_id == "b"


def test_all_unaffordable_and_empty_auctions_produce_no_winner():
    """REQ-ADS-ARCH-006: negative test never charges an unaffordable or empty auction."""
    bids = _bids(_record("a", 101, 100))
    assert choose_winner(bids, {"a": 100}, _budgets(bids)) is None
    assert choose_winner({}, {}, {}) is None


@pytest.mark.parametrize("score", [True, False, -1, 101, 0.5, "90", None, float("nan"), float("inf")])
def test_engine_rejects_invalid_relevance(score):
    """REQ-ADS-NFR-SAFETY-007, REQ-ADS-ARCH-009: negative test prevents numeric coercion."""
    bids = _bids(_record())
    with pytest.raises(BidError):
        choose_winner(bids, {"a": score}, _budgets(bids))


@pytest.mark.parametrize("changes", [
    {"total_cents": True}, {"spent_cents": False}, {"remaining_cents": 100.0},
    {"remaining_cents": float("nan")}, {"spent_cents": -1, "remaining_cents": 101},
    {"spent_cents": 101, "remaining_cents": -1}, {"spent_cents": 3, "remaining_cents": 98},
])
def test_engine_refuses_inconsistent_or_noninteger_budget_snapshots(changes):
    """REQ-ADS-ARCH-005/008, REQ-ADS-NFR-SAFETY-007: negative test validates budget arithmetic."""
    bids = _bids(_record())
    budgets = _budgets(bids)
    budgets["a"].update(changes)
    with pytest.raises(BidError):
        choose_winner(bids, {"a": 90}, budgets)


def test_hundred_candidate_offline_compute_median_below_fifty_ms():
    """REQ-ADS-NFR-PERF-002, REQ-ADS-NFR-QA-003: measured 100-candidate pure auction."""
    bids = _bids(*[_record(f"ad_{index:03}", index + 1, 1000) for index in range(100)])
    scores = {ad_id: 100 for ad_id in bids}
    budgets = _budgets(bids)
    durations = []
    for _ in range(31):
        started = time.perf_counter()
        winner = choose_winner(bids, scores, budgets)
        durations.append(time.perf_counter() - started)
        assert winner is not None and winner.ad_id == "ad_099"
    assert statistics.median(durations) < 0.050


def test_ledger_seed_and_repeated_seed_preserve_spend(ledger):
    """REQ-ADS-ARCH-005/007/008: persisted seed is idempotent and cannot reset spend."""
    bids = _bids(_record())
    ledger.seed(bids)
    assert ledger.budgets()["a"] == dict(total_cents=100, spent_cents=0, remaining_cents=100, status="active")
    _commit(ledger, "r1")
    ledger.seed(bids)
    assert ledger.budgets()["a"] == dict(total_cents=100, spent_cents=7, remaining_cents=93, status="active")
    for changed in (_record(bid_cents=8), _record(budget_cents=101), _record(status="paused")):
        with pytest.raises(LedgerError):
            ledger.seed(_bids(changed))
        assert ledger.budgets()["a"]["spent_cents"] == 7


def test_seed_zero_and_paused_budgets(ledger):
    """REQ-ADS-ARCH-005/006, REQ-ADS-FR-007: seed starts at zero spend and exhausts zero total."""
    ledger.seed(_bids(_record("a", budget_cents=0), _record("b", status="paused")))
    assert ledger.budgets()["a"] == dict(total_cents=0, spent_cents=0, remaining_cents=0, status="exhausted")
    assert ledger.budgets()["b"] == dict(total_cents=100, spent_cents=0, remaining_cents=100, status="paused")


def test_commit_returns_exact_cached_result_with_one_audit(ledger):
    """REQ-ADS-ARCH-007, REQ-ADS-FR-008, INV-ADS-012: retry is one logical transaction."""
    ledger.seed(_bids(_record()))
    assert ledger.lookup("r1", "fingerprint") is None
    saved = _commit(ledger, "r1", "fingerprint")
    assert ledger.lookup("r1", "fingerprint") == saved
    retry = ledger.finalize("r1", "fingerprint", _no_ad("r1"), {"changed": True})
    assert retry == saved
    assert ledger.budgets()["a"]["spent_cents"] == 7
    audits = ledger.audit_records()
    assert len(audits) == 1
    assert audits[0]["request_id"] == "r1"
    assert audits[0]["audit_id"] == saved["audit_id"]
    assert audits[0]["final"] == saved


def test_request_id_fingerprint_conflict_cannot_charge_again(ledger):
    """REQ-ADS-ARCH-007, INV-ADS-012: negative test blocks reused ID with changed input."""
    ledger.seed(_bids(_record()))
    original = _commit(ledger, "r1", "first")
    with pytest.raises(RequestConflict):
        ledger.lookup("r1", "second")
    with pytest.raises(RequestConflict):
        _commit(ledger, "r1", "second")
    assert ledger.lookup("r1", "first") == original
    assert ledger.budgets()["a"]["spent_cents"] == 7
    assert len(ledger.audit_records()) == 1


@pytest.mark.parametrize("charge", [True, False, 0, -1, 6, 8, 7.0, "7", float("nan"), float("inf")])
def test_ledger_refuses_invalid_or_non_bid_charges_atomically(ledger, charge):
    """REQ-ADS-ARCH-007/008/010: negative test rejects forged price and noninteger money."""
    ledger.seed(_bids(_record()))
    before = ledger.budgets()
    with pytest.raises(LedgerError):
        ledger.finalize("invalid", "input", _ad_result("invalid"), {}, ad_id="a", charge_cents=charge)
    assert ledger.budgets() == before
    assert ledger.lookup("invalid", "input") is None
    assert ledger.audit_records() == []


def test_spend_replay_exact_exhaustion_and_overspend_rejection(ledger):
    """REQ-ADS-ARCH-005/006/007/008, REQ-ADS-FR-007: integer replay has zero discrepancy."""
    ledger.seed(_bids(_record(budget_cents=21)))
    prices = []
    for index in range(3):
        _commit(ledger, f"r{index}")
        prices.append(7)
        budget = ledger.budgets()["a"]
        assert budget["spent_cents"] == sum(prices)
        assert budget["remaining_cents"] == budget["total_cents"] - budget["spent_cents"]
        assert 0 <= budget["spent_cents"] <= budget["total_cents"]
        assert all(type(budget[key]) is int for key in ("total_cents", "spent_cents", "remaining_cents"))
    assert ledger.budgets()["a"]["status"] == "exhausted"
    with pytest.raises(InsufficientBudget):
        _commit(ledger, "too-late")
    assert ledger.lookup("too-late", "too-late") is None
    assert len(ledger.audit_records()) == 3
    assert ledger.budgets()["a"]["spent_cents"] == 21


def test_no_ad_is_audited_without_debit(ledger):
    """REQ-ADS-FR-008, INV-ADS-012: completed no-ad request still has one canonical audit."""
    ledger.seed(_bids(_record()))
    saved = ledger.finalize("none", "input", _no_ad("none"), {"case": "no-ad"})
    assert ledger.lookup("none", "input") == saved
    assert ledger.budgets()["a"]["spent_cents"] == 0
    assert len(ledger.audit_records()) == 1
    assert ledger.audit_records()[0]["final"] == saved


@pytest.mark.parametrize("bad_field", ["result", "evidence"])
def test_unserializable_transaction_payload_cannot_leave_a_debit(ledger, bad_field):
    """REQ-ADS-ARCH-007, REQ-ADS-FR-008, INV-ADS-012: negative test preserves atomic evidence."""
    ledger.seed(_bids(_record()))
    result = _ad_result("bad-payload")
    evidence = {"case": "serialization-fault"}
    target = result if bad_field == "result" else evidence
    target["invalid"] = object()
    with pytest.raises(LedgerError):
        ledger.finalize("bad-payload", "input", result, evidence, ad_id="a", charge_cents=7)
    assert ledger.budgets()["a"]["spent_cents"] == 0
    assert ledger.lookup("bad-payload", "input") is None
    assert ledger.audit_records() == []


@pytest.mark.parametrize("failed_stage", ["after_debit", "before_audit", "before_commit"])
def test_injected_transaction_failure_rolls_back_every_boundary(failed_stage):
    """REQ-ADS-ARCH-005/007, REQ-ADS-FR-008, INV-ADS-012: negative test proves atomic rollback."""
    calls = []
    fail = True

    def hook(stage):
        calls.append(stage)
        if fail and stage == failed_stage:
            raise OSError("independent injected storage failure")

    instance = Ledger(fault_hook=hook)
    try:
        instance.seed(_bids(_record()))
        with pytest.raises(LedgerError):
            _commit(instance, "retryable")
        assert failed_stage in calls
        assert instance.budgets()["a"]["spent_cents"] == 0
        assert instance.lookup("retryable", "retryable") is None
        assert instance.audit_records() == []
        fail = False
        saved = _commit(instance, "retryable")
        assert instance.lookup("retryable", "retryable") == saved
        assert instance.budgets()["a"]["spent_cents"] == 7
        assert len(instance.audit_records()) == 1
    finally:
        instance.close()


def test_file_restart_preserves_spend_idempotency_and_audit():
    """REQ-ADS-ARCH-005/007, REQ-ADS-FR-008: durable transaction survives closing and reopening."""
    with _file_ledger_path() as path:
        first = Ledger(path)
        try:
            first.seed(_bids(_record()))
            saved = _commit(first, "durable")
        finally:
            first.close()
        second = Ledger(path)
        try:
            second.seed(_bids(_record()))
            assert second.budgets()["a"]["spent_cents"] == 7
            assert second.lookup("durable", "durable") == saved
            assert _commit(second, "durable") == saved
            assert len(second.audit_records()) == 1
            assert second.audit_records()[0]["final"] == saved
        finally:
            second.close()


@pytest.mark.parametrize("same_request", [False, True])
def test_independent_file_connections_cannot_overspend_or_double_charge(same_request):
    """REQ-ADS-ARCH-005/006/007, INV-ADS-012: negative test exercises real concurrent transactions."""
    with _file_ledger_path() as path:
        initial = Ledger(path)
        try:
            initial.seed(_bids(_record(budget_cents=7)))
        finally:
            initial.close()
        barrier = threading.Barrier(2)

        def compete(index):
            instance = Ledger(path)
            try:
                barrier.wait(timeout=10)
                try:
                    return _commit(instance, "same" if same_request else f"r{index}")
                except InsufficientBudget:
                    return "insufficient"
            finally:
                instance.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(compete, range(2)))
        if same_request:
            assert results[0] == results[1]
            assert isinstance(results[0], dict)
        else:
            assert sum(isinstance(value, dict) for value in results) == 1
            assert results.count("insufficient") == 1
        final = Ledger(path)
        try:
            assert final.budgets()["a"] == dict(
                total_cents=7, spent_cents=7, remaining_cents=0, status="exhausted",
            )
            assert len(final.audit_records()) == 1
        finally:
            final.close()
