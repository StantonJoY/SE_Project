"""Strict bid contracts for ADR-005 §2's deterministic auction boundary.

Enforces REQ-ADS-NFR-SAFETY-006, REQ-ADS-NFR-SAFETY-007,
REQ-ADS-ARCH-008 and REQ-ADS-SEC-002. Money is integer cents; validation
never coerces strings, booleans or floating point values into money.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, fields


class BidError(ValueError):
    """A bid or auction input violates ADR-005 §2's numeric contract."""


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    """Reject non-integer values for REQ-ADS-ARCH-008, including bool."""
    if type(value) is not int or value < minimum:
        raise BidError(f"{name} must be an integer >= {minimum}")
    return value


def _identifier(value: object, name: str = "ad_id") -> str:
    """Check identifiers without coercion (REQ-ADS-SEC-002)."""
    if not isinstance(value, str) or not value.strip():
        raise BidError(f"{name} must be a nonempty string")
    return value


@dataclass(frozen=True)
class Bid:
    """Validated immutable offer; ADR-005 §2, REQ-ADS-NFR-SAFETY-006."""

    ad_id: str
    bid_cents: int
    budget_cents: int
    bid_floor: int = 1
    bid_ceiling: int = 1_000_000
    status: str = "active"

    def __post_init__(self) -> None:
        """Enforce integer money and legal bounds (REQ-ADS-ARCH-008)."""
        _identifier(self.ad_id)
        _integer(self.bid_cents, "bid_cents", minimum=1)
        _integer(self.budget_cents, "budget_cents")
        _integer(self.bid_floor, "bid_floor", minimum=1)
        _integer(self.bid_ceiling, "bid_ceiling", minimum=1)
        if not self.bid_floor <= self.bid_cents <= self.bid_ceiling:
            raise BidError("bid_cents must lie within bid_floor and bid_ceiling")
        if not isinstance(self.status, str) or self.status not in {
            "active", "paused", "exhausted"
        }:
            raise BidError("status must be active, paused or exhausted")


def validate_bids(
    records: list[dict], known_ad_ids: Collection[str] | None = None,
) -> dict[str, Bid]:
    """Validate a whole batch, rejecting duplicates/unknowns (ADR-005 §2).

    Implements REQ-ADS-NFR-SAFETY-006 and REQ-ADS-SEC-002. One invalid
    record rejects the batch; the caller never receives a partial result.
    """
    if not isinstance(records, list):
        raise BidError("bid records must be a list")
    if known_ad_ids is not None and (
        not isinstance(known_ad_ids, Collection)
        or isinstance(known_ad_ids, (str, bytes))
    ):
        raise BidError("known_ad_ids must be a collection of identifiers")
    if known_ad_ids is not None:
        for ad_id in known_ad_ids:
            _identifier(ad_id, "known ad_id")
    allowed = {field.name for field in fields(Bid)}
    required = {"ad_id", "bid_cents", "budget_cents"}
    bids: dict[str, Bid] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise BidError(f"bid record {index} must be an object")
        if not required <= record.keys() or record.keys() - allowed:
            raise BidError(f"bid record {index} has missing or unknown fields")
        bid = Bid(**record)
        if bid.ad_id in bids:
            raise BidError(f"duplicate ad_id: {bid.ad_id}")
        if known_ad_ids is not None and bid.ad_id not in known_ad_ids:
            raise BidError(f"unknown ad_id: {bid.ad_id}")
        bids[bid.ad_id] = bid
    return bids
