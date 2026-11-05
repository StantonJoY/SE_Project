"""Pure pay-as-bid auction, following ADR-005 §2.

Enforces REQ-ADS-ARCH-006, REQ-ADS-ARCH-009, REQ-ADS-ARCH-010,
REQ-ADS-ARCH-011, REQ-ADS-ARCH-012 and REQ-ADS-FR-005/006. The only score
formula is integer relevance * bid_cents; this module has no I/O or LLM calls.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .models import Bid, BidError, _identifier, _integer


@dataclass(frozen=True)
class AuctionChoice:
    """Deterministic winner and pay-as-bid price (REQ-ADS-ARCH-010/012)."""

    ad_id: str
    bid_cents: int
    relevance: int
    score: int
    price_cents: int


def choose_winner(
    bids: Mapping[str, Bid], scores: Mapping[str, int],
    budgets: Mapping[str, dict],
) -> AuctionChoice | None:
    """Select the highest positive score, ties by ad_id (ADR-005 §2).

    Implements REQ-ADS-FR-005/006 and REQ-ADS-ARCH-005/006/009/010/011.
    Scores must cover exactly the offered candidate IDs. The budget snapshot
    may contain other ads. All candidate data is validated before selection,
    so malformed losing or paused offers cannot be silently ignored.
    Settlement independently rechecks current affordability in the ledger.
    """
    if not all(isinstance(value, Mapping) for value in (bids, scores, budgets)):
        raise BidError("bids, scores and budgets must be mappings")
    if set(scores) != set(bids):
        raise BidError("scores must cover exactly the candidate bid IDs")
    choices: list[AuctionChoice] = []
    for ad_id, bid in bids.items():
        _identifier(ad_id)
        if not isinstance(bid, Bid) or ad_id != bid.ad_id:
            raise BidError("each bid must be a Bid matching its mapping key")
        bid.__post_init__()
        relevance = _integer(scores[ad_id], f"relevance for {ad_id}")
        if relevance > 100:
            raise BidError("relevance must lie within 0 and 100")
        budget = budgets.get(ad_id)
        if not isinstance(budget, dict):
            raise BidError(f"missing or invalid budget for {ad_id}")
        required = {"total_cents", "spent_cents", "remaining_cents", "status"}
        if not required <= budget.keys():
            raise BidError(f"budget fields missing for {ad_id}")
        total = _integer(budget["total_cents"], "total_cents")
        spent = _integer(budget["spent_cents"], "spent_cents")
        remaining = _integer(budget["remaining_cents"], "remaining_cents")
        if spent > total or remaining != total - spent:
            raise BidError(f"budget invariant violated for {ad_id}")
        status = budget["status"]
        if not isinstance(status, str) or status not in {
            "active", "paused", "exhausted"
        }:
            raise BidError(f"invalid budget status for {ad_id}")
        if "bid_cents" in budget:
            persisted_bid = _integer(budget["bid_cents"], "bid_cents", minimum=1)
            if persisted_bid != bid.bid_cents:
                raise BidError(f"bid differs from budget contract for {ad_id}")
        if (relevance == 0 or bid.status != "active" or status != "active"
                or remaining < bid.bid_cents):
            continue
        choices.append(AuctionChoice(
            ad_id=ad_id, bid_cents=bid.bid_cents, relevance=relevance,
            score=relevance * bid.bid_cents, price_cents=bid.bid_cents,
        ))
    return min(choices, key=lambda choice: (-choice.score, choice.ad_id), default=None)
