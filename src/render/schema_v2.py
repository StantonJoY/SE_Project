"""Closed V2 public result contract, independent of V1 rendering.

Implements: ADR-005 (transactional pay-as-bid outcome).
Verifies: REQ-ADS-ARCH-005/007/008/010; REQ-ADS-FR-004.
"""

from __future__ import annotations

import re


def validate_v2_result(result: dict) -> list[str]:
    """Return diagnostics for fields, strict types, score and budget arithmetic."""
    errors: list[str] = []
    if not isinstance(result, dict):
        return ["result must be an object"]
    kind = result.get("kind")
    fields = {
        "ad": {"kind", "request_id", "audit_id", "ad", "explanation", "auction"},
        "no_ad": {"kind", "request_id", "audit_id", "reason_code", "detail"},
        "status_unknown": {"kind", "request_id", "detail", "retry_same_request"},
    }
    if not isinstance(kind, str) or kind not in fields:
        return ["unknown result kind"]
    if set(result) != fields[kind]:
        errors.append("missing or extra result fields")
    if not isinstance(result.get("request_id"), str) or (not result["request_id"].strip() and result.get("reason_code") != "request_invalid"):
        errors.append("request_id must be a nonempty string")
    if kind == "status_unknown":
        if result.get("retry_same_request") is not True:
            errors.append("status_unknown requires retry_same_request=true")
    else:
        audit = result.get("audit_id")
        if not isinstance(audit, str) or (not audit and result.get("reason_code") not in {"request_conflict", "request_invalid"}):
            errors.append("audit_id must be a nonempty string for finalized results")
    if kind in {"no_ad", "status_unknown"}:
        if not isinstance(result.get("detail"), str) or not result["detail"].strip():
            errors.append("detail must be a nonempty string")
        if kind == "no_ad" and (not isinstance(result.get("reason_code"), str) or not result["reason_code"]):
            errors.append("reason_code must be a nonempty string")
        return errors
    ad = result.get("ad")
    if not isinstance(ad, dict) or set(ad) != {"ad_id", "title", "copy", "category"}:
        errors.append("ad fields are invalid")
    elif any(not isinstance(ad[k], str) or not ad[k] for k in ad):
        errors.append("ad values must be nonempty strings")
    elif not re.fullmatch(r"ad_[0-9]+", ad["ad_id"]):
        errors.append("ad_id format is invalid")
    if not isinstance(result.get("explanation"), str):
        errors.append("explanation must be a string")
    auction = result.get("auction")
    auction_fields = {"bid_cents", "relevance", "score", "price_cents", "budget_before_cents", "budget_after_cents"}
    if not isinstance(auction, dict) or set(auction) != auction_fields:
        errors.append("auction fields are invalid")
        return errors
    if any(type(auction[k]) is not int for k in auction_fields):
        errors.append("auction values must be strict integers")
        return errors
    if not 0 < auction["bid_cents"] <= 1_000_000 or auction["price_cents"] != auction["bid_cents"]:
        errors.append("price must equal a positive bounded bid")
    if not 1 <= auction["relevance"] <= 100 or auction["score"] != auction["relevance"] * auction["bid_cents"]:
        errors.append("score must equal positive relevance times bid")
    if auction["budget_after_cents"] < 0 or auction["budget_before_cents"] - auction["price_cents"] != auction["budget_after_cents"]:
        errors.append("budget math is invalid")
    return errors
