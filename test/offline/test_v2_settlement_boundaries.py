"""Postimplementation VERIFY counterexamples for ADR-005 settlement contracts.

Verifies REQ-ADS-ARCH-005/006/007/008/010, REQ-ADS-SEC-002,
REQ-ADS-FR-008 and INV-V2-001/002/004/005/008/010/011.
These tests exercise public inputs and real SQLite transactions; they are
supplementary evidence, not claimed to be human-approved preimplementation tests.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from bidding import Bid, BidError, Ledger, LedgerError, choose_winner, validate_bids


def _offer():
    return {"a": Bid("a", 7, 100)}


def _snapshot():
    return {"a": {"total_cents": 100, "spent_cents": 0, "remaining_cents": 100, "status": "active"}}


def _ad():
    return {"kind": "ad", "request_id": "r", "audit_id": "audit-r", "ad": {"ad_id": "a"}, "auction": {}}


@pytest.fixture
def ledger():
    with Ledger() as instance:
        instance.seed(_offer())
        yield instance


def _assert_uncommitted(ledger):
    assert ledger.budgets() == _snapshot()
    assert ledger.lookup("r", "input") is None
    assert ledger.audit_records() == []


@pytest.mark.parametrize("records", [None, {}, (), [None], [7]])
def test_bid_loader_rejects_non_batch_and_non_object_records(records):
    """REQ-ADS-SEC-002, INV-V2-001: malformed batches must not become partial offers."""
    with pytest.raises(BidError):
        validate_bids(records)


@pytest.mark.parametrize("known_ids", ["a", b"a", 1, [""]])
def test_bid_loader_rejects_invalid_authoritative_id_collection(known_ids):
    """REQ-ADS-SEC-002: a malformed known-ID authority must not silently admit an offer."""
    with pytest.raises(BidError):
        validate_bids([{"ad_id": "a", "bid_cents": 7, "budget_cents": 100}], known_ids)


@pytest.mark.parametrize("field", ["bids", "scores", "budgets"])
def test_auction_rejects_non_mapping_contracts(field):
    """REQ-ADS-ARCH-009, INV-V2-006: invalid authority inputs cannot produce a winner."""
    inputs = {"bids": _offer(), "scores": {"a": 90}, "budgets": _snapshot()}
    inputs[field] = []
    with pytest.raises(BidError):
        choose_winner(**inputs)


@pytest.mark.parametrize("scores", [{}, {"b": 90}, {"a": 90, "b": 1}])
def test_auction_requires_exact_score_identity_set(scores):
    """REQ-ADS-SEC-002, INV-V2-007: omitted or foreign scores must reject the whole auction."""
    with pytest.raises(BidError):
        choose_winner(_offer(), scores, _snapshot())


@pytest.mark.parametrize("bids", [{"a": {}}, {"a": Bid("different", 7, 100)}])
def test_auction_rejects_wrong_offer_type_or_identity(bids):
    """REQ-ADS-SEC-002, INV-V2-001: unvalidated or mismatched offers cannot be ranked."""
    with pytest.raises(BidError):
        choose_winner(bids, {"a": 90}, _snapshot())


@pytest.mark.parametrize("budgets", [{}, {"a": None}, {"a": {"remaining_cents": 100}}])
def test_auction_requires_complete_budget_contract(budgets):
    """REQ-ADS-ARCH-005/006: missing economic authority cannot be interpreted as affordability."""
    with pytest.raises(BidError):
        choose_winner(_offer(), {"a": 90}, budgets)


@pytest.mark.parametrize("changes", [
    {"total_cents": 10, "spent_cents": 11, "remaining_cents": 0},
    {"status": "unknown"}, {"status": ["active"]}, {"bid_cents": 8}, {"bid_cents": True},
])
def test_auction_rejects_broken_budget_authority(changes):
    """REQ-ADS-ARCH-005/008/010, INV-V2-002: an inconsistent losing offer still rejects."""
    offers = {**_offer(), "b": Bid("b", 1, 1)}
    budgets = {**_snapshot(), "b": {"total_cents": 1, "spent_cents": 0, "remaining_cents": 1, "status": "active"}}
    budgets["a"].update(changes)
    before = copy.deepcopy(budgets)
    with pytest.raises(BidError):
        choose_winner(offers, {"a": 0, "b": 100}, budgets)
    assert budgets == before


@pytest.mark.parametrize("path", [None, ""])
def test_invalid_storage_location_is_explicit_failure(path):
    """REQ-ADS-GOV-001: invalid persistence configuration cannot masquerade as a working ledger."""
    with pytest.raises(LedgerError):
        Ledger(path)


def test_directory_cannot_masquerade_as_a_database_file():
    """REQ-ADS-GOV-001: actual SQLite initialization errors have the public error type."""
    with pytest.raises(LedgerError):
        Ledger(ROOT)


def test_invalid_fault_hook_is_rejected_at_construction():
    """REQ-ADS-ARCH-007: bad instrumentation must not create a partially usable ledger."""
    with pytest.raises(LedgerError):
        Ledger(fault_hook="not-callable")


@pytest.mark.parametrize("seed", [[], {"a": {}}, {"a": Bid("wrong", 7, 100)}])
def test_seed_rejects_non_authoritative_offer_contract_without_mutation(ledger, seed):
    """REQ-ADS-ARCH-005/008, INV-V2-001: a failed seed preserves the original offer and balances."""
    with pytest.raises(LedgerError):
        ledger.seed(seed)
    _assert_uncommitted(ledger)


@pytest.mark.parametrize("method,args", [
    ("lookup", ("", "input")), ("lookup", ("r", "")),
    ("finalize", ("", "input", {}, {})), ("finalize", ("r", "", {}, {})),
])
def test_request_identity_is_mandatory_before_transaction(ledger, method, args):
    """REQ-ADS-ARCH-007, INV-V2-010: a missing request identity cannot create anonymous accounting."""
    with pytest.raises(LedgerError):
        getattr(ledger, method)(*args)
    _assert_uncommitted(ledger)


@pytest.mark.parametrize("field", ["result", "evidence"])
def test_transaction_requires_structured_result_and_evidence(ledger, field):
    """REQ-ADS-FR-008, INV-V2-011: a non-object payload cannot bypass canonical evidence."""
    inputs = {"result": _ad(), "evidence": {"case": "boundary"}}
    inputs[field] = []
    with pytest.raises(LedgerError):
        ledger.finalize("r", "input", **inputs, ad_id="a", charge_cents=7)
    _assert_uncommitted(ledger)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_evidence_never_commits_spend(ledger, value):
    """REQ-ADS-NFR-SAFETY-007, INV-V2-005/011: non-finite evidence fails before any debit."""
    with pytest.raises(LedgerError):
        ledger.finalize("r", "input", _ad(), {"value": value}, ad_id="a", charge_cents=7)
    _assert_uncommitted(ledger)


@pytest.mark.parametrize("changes", [
    {"request_id": "other"}, {"audit_id": ""}, {"kind": "invented"},
    {"kind": "no_ad"}, {"ad": None}, {"ad": {"ad_id": "other"}},
])
def test_result_identity_and_kind_cannot_disagree_with_charged_settlement(ledger, changes):
    """REQ-ADS-ARCH-007/010, INV-V2-004/011: forged result identities leave no economic trace."""
    result = _ad()
    result.update(changes)
    with pytest.raises(LedgerError):
        ledger.finalize("r", "input", result, {}, ad_id="a", charge_cents=7)
    _assert_uncommitted(ledger)


@pytest.mark.parametrize("winner", ["", "unseeded"])
def test_winner_must_be_an_identified_seeded_offer(ledger, winner):
    """REQ-ADS-SEC-002, INV-V2-001: foreign economic identity cannot acquire a debit entry."""
    result = _ad()
    result["ad"]["ad_id"] = winner
    with pytest.raises(LedgerError):
        ledger.finalize("r", "input", result, {}, ad_id=winner, charge_cents=7)
    _assert_uncommitted(ledger)


@pytest.mark.parametrize("kind,charge", [("no_ad", 7), ("ad", 0)])
def test_no_winner_cannot_have_a_charge_or_ad_result(ledger, kind, charge):
    """REQ-ADS-ARCH-007/010, INV-V2-008: no-winner and charged-ad contracts cannot be mixed."""
    result = _ad()
    result["kind"] = kind
    with pytest.raises(LedgerError):
        ledger.finalize("r", "input", result, {}, charge_cents=charge)
    _assert_uncommitted(ledger)


def test_invalid_auction_shape_rolls_back_even_after_debit(ledger):
    """REQ-ADS-ARCH-007, INV-V2-004: a late output error rolls back the real SQL debit."""
    result = _ad()
    result["auction"] = []
    with pytest.raises(LedgerError):
        ledger.finalize("r", "input", result, {}, ad_id="a", charge_cents=7)
    _assert_uncommitted(ledger)
    # Rollback also releases the transaction: this same request can safely succeed once.
    saved = ledger.finalize("r", "input", _ad(), {}, ad_id="a", charge_cents=7)
    assert saved["auction"]["budget_after_cents"] == 93
    assert ledger.budgets()["a"]["spent_cents"] == 7
    assert len(ledger.audit_records()) == 1


def test_caller_mutation_cannot_rewrite_durable_response_or_evidence(ledger):
    """REQ-ADS-FR-008, INV-V2-010/011: snapshots are isolated from caller-owned dictionaries."""
    result = _ad()
    evidence = {"nested": {"approved": True}}
    saved = ledger.finalize("r", "input", result, evidence, ad_id="a", charge_cents=7)
    result["ad"]["ad_id"] = "changed"
    evidence["nested"]["approved"] = False
    saved["ad"]["ad_id"] = "also-changed"
    replay = ledger.lookup("r", "input")
    assert replay["ad"]["ad_id"] == "a"
    assert ledger.audit_records()[0]["evidence"] == {"nested": {"approved": True}}
    assert ledger.budgets()["a"]["spent_cents"] == 7


@pytest.mark.parametrize("method,args", [
    ("budgets", ()), ("lookup", ("r", "input")),
    ("finalize", ("r", "input", _ad(), {})), ("seed", (_offer(),)),
    ("audit_records", ()), ("__enter__", ()),
])
def test_closed_ledger_cannot_serve_or_accept_authoritative_state(method, args):
    """REQ-ADS-GOV-001, INV-V2-004: closed infrastructure explicitly refuses every state operation."""
    instance = Ledger()
    instance.seed(_offer())
    instance.close()
    instance.close()
    with pytest.raises(LedgerError):
        getattr(instance, method)(*args)
