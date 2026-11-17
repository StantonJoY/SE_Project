"""V2 orchestration: sanitized relevance advice, compliance, then atomic charge/audit.

Implements: ADR-005; ADR-001 §2 (compliance final authority).
Verifies: REQ-ADS-ARCH-005/006/007/008/009/010/011/012, REQ-ADS-FR-005/006/007/008;
REQ-ADS-SEC-001, INV-ADS-001/004/012.
The ledger's request table is read for idempotency; audit history is never read.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from app.sanitize import scan_for_injection
from bidding import Bid, BidError, InsufficientBudget, Ledger, RequestConflict, choose_winner, validate_bids
from compliance.pipeline import run_compliance
from compliance.rules import SceneRules
from render.schema_v2 import validate_v2_result
from scene.parser import SceneInputError, parse_scene
from selector.relevance import (
    RELEVANCE_PROMPT_VERSION,
    RelevanceClient,
    RelevanceError,
    estimate_relevance_tokens,
    parse_relevance_output,
    validate_unicode_data,
)


def _stable_value(value: Any) -> Any:
    """Represent even rejected inputs deterministically without invoking repr on secrets."""
    if is_dataclass(value) and not isinstance(value, type):
        return _stable_value(asdict(value))
    if value is None or type(value) in {str, bool, int}:
        return value
    if isinstance(value, float):
        return {"__float__": str(value)}
    if isinstance(value, Mapping):
        return {str(k): _stable_value(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (tuple, list)):
        return [_stable_value(v) for v in value]
    return {"__invalid_type__": type(value).__name__}


def _fingerprint(value: Any) -> str:
    # ASCII canonical JSON preserves rejected lone-surrogate evidence losslessly
    # without attempting to encode invalid scalar values as UTF-8.
    payload = json.dumps(_stable_value(value), sort_keys=True, ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _unknown(request_id: str) -> dict:
    return {"kind": "status_unknown", "request_id": request_id, "retry_same_request": True,
            "detail": "Storage outcome is unknown; retry the identical request with the same request_id. No charge amount is asserted."}


def _explanation(reason: str, banned_words: BannedWords) -> str:
    """Read-only display text: it cannot change the chosen ID, price or compliance result."""
    fallback = "根据相关性与出价计算得分，并已通过确定性合规检查。"
    if len(reason.strip()) < 8 or banned_words.check(reason) is not None or not scan_for_injection(reason).clean:
        return fallback
    return reason


def recommend_v2(
    raw_scene: object, *, request_id: str, repo: AdRepository, bids: Mapping[str, Bid],
    client: RelevanceClient, ledger: Ledger, banned_words: BannedWords, rules: SceneRules,
    model_version: str = "fixed-v2", policy_version: str = "pay-as-bid-v1",
    context_budget_tokens: int = 2000,
) -> dict:
    """REQ-ADS-ARCH-007/FR-008: replay once, with compliance strictly before debit.

    A storage failure never implies zero charge. A successful no_ad is saved atomically
    with a zero charge; a concurrent budget loss is rolled back before saving no_ad.
    """
    if not isinstance(request_id, str) or not request_id.strip():
        return {"kind": "no_ad", "request_id": request_id if isinstance(request_id, str) else "",
                "audit_id": "", "reason_code": "request_invalid", "detail": "request_id must be a nonempty string."}
    try:
        validate_unicode_data(request_id)
    except RelevanceError:
        # An invalid identity cannot be bound to SQLite or echoed as UTF-8.
        # This is an input rejection, not evidence of storage uncertainty.
        return {"kind": "no_ad", "request_id": "", "audit_id": "", "reason_code": "request_invalid",
                "detail": "request_id contains invalid Unicode scalar values."}
    scene = None
    scene_error = ""
    try:
        validate_unicode_data(raw_scene)
        scene = parse_scene(raw_scene)
        normalized_scene = asdict(scene)
        normalized_scene["user_tags"] = list(scene.user_tags)
    except (SceneInputError, RelevanceError) as exc:
        normalized_scene = _stable_value(raw_scene)
        scene_error = str(exc)

    # All decision inputs are fingerprinted, including unseeded/paused bids. Mutable
    # budgets are deliberately excluded so retry after a charge returns the saved result.
    fingerprint = _fingerprint({
        "scene": normalized_scene, "bids": bids, "materials": repo.all(),
        "rules": rules, "banned_words": banned_words.words, "model_version": model_version,
        "policy_version": policy_version, "prompt_version": RELEVANCE_PROMPT_VERSION,
        "context_budget_tokens": context_budget_tokens,
    })
    try:
        saved = ledger.lookup(request_id, fingerprint)
        if saved is not None:
            return saved
    except RequestConflict:
        return {"kind": "no_ad", "request_id": request_id, "audit_id": "",
                "reason_code": "request_conflict", "detail": "request_id already belongs to different inputs; no new charge was attempted."}
    except Exception:  # noqa: BLE001 - storage may have failed before lookup completed
        return _unknown(request_id)

    audit_id = "aud-v2-" + hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:24]
    evidence: dict = {
        "scene": normalized_scene, "bids": _stable_value(bids), "budgets": {},
        "scores": {}, "candidate_ids": [], "raw_relevance_output": None,
        "provenance": {"model_version": model_version, "prompt_version": RELEVANCE_PROMPT_VERSION,
                       "policy_version": policy_version, "score_formula": "relevance_times_bid"},
        "context": {"budget_tokens": context_budget_tokens, "estimated_tokens": 0,
                    "estimator": "utf8_byte_estimate_not_provider_tokenizer",
                    "standing_constraints_present": True},
        "compliance": {"approved": False, "executed": False, "results": []},
    }

    def no_ad(code: str, detail: str) -> dict:
        result = {"kind": "no_ad", "request_id": request_id, "audit_id": audit_id,
                  "reason_code": code, "detail": detail}
        try:
            return ledger.finalize(request_id, fingerprint, result, evidence)
        except RequestConflict:
            return {"kind": "no_ad", "request_id": request_id, "audit_id": "",
                    "reason_code": "request_conflict", "detail": "request_id was finalized with different inputs; no new charge was attempted."}
        except Exception:  # noqa: BLE001 - uncertain commit must not claim zero charge
            return _unknown(request_id)

    if scene is None:
        return no_ad("scene_invalid", scene_error)
    if policy_version != "pay-as-bid-v1" or not isinstance(model_version, str) or not model_version:
        return no_ad("configuration_invalid", "Unsupported policy or missing model version.")
    if type(context_budget_tokens) is not int or not 0 < context_budget_tokens <= 2000:
        return no_ad("budget_exceeded", "Context budget must be an integer within 1..2000 estimated tokens.")
    try:
        records = []
        for ad_id, bid in bids.items():
            if not isinstance(bid, Bid) or ad_id != bid.ad_id:
                raise BidError("bid mapping and validated IDs differ")
            records.append(asdict(bid))
        valid_bids = validate_bids(records, known_ad_ids={ad.ad_id for ad in repo.all()})
    except (BidError, TypeError, ValueError):
        return no_ad("bids_invalid", "Bid inputs failed strict validation.")
    try:
        budgets = ledger.budgets()
        evidence["budgets"] = budgets
    except Exception:  # noqa: BLE001 - no reliable budget observation
        return _unknown(request_id)
    candidates = repo.filter_by_scene(scene)
    evidence["prefilter_candidate_ids"] = [ad.ad_id for ad in candidates]
    eligible = []
    for ad in candidates:
        bid, budget = valid_bids.get(ad.ad_id), budgets.get(ad.ad_id)
        if bid is None or budget is None:
            continue
        # Startup seeds immutable bid terms. A mismatched injected mapping is not
        # allowed to score one bid and debit a different ledger bid.
        if budget.get("bid_cents", bid.bid_cents) != bid.bid_cents or budget["total_cents"] != bid.budget_cents:
            return no_ad("bids_invalid", "Bid terms differ from the durable ledger seed.")
        if bid.status == "active" and budget["status"] == "active" and budget["remaining_cents"] >= bid.bid_cents:
            eligible.append(ad)
    evidence["candidate_ids"] = [ad.ad_id for ad in eligible]
    if not eligible:
        return no_ad("no_candidates", "No scene-compatible active bid has sufficient remaining budget.")
    summaries = [{"ad_id": ad.ad_id, "title": ad.title,
                  "category": ad.category, "target_tags": list(ad.target_tags)} for ad in eligible]
    # Scan original text, including newlines, before JSON escaping can conceal
    # whitespace-sensitive injection patterns. Copy is scanned but not transmitted.
    untrusted_text = [scene.time_slot, scene.device, *scene.user_tags]
    for ad in eligible:
        untrusted_text.extend([ad.ad_id, ad.title, ad.copy, ad.category, *ad.target_tags])
    try:
        validate_unicode_data(untrusted_text)
    except RelevanceError:
        return no_ad("input_invalid", "Candidate or scene text contains invalid Unicode scalar values.")
    sanitize = scan_for_injection("\n".join(untrusted_text))
    if not sanitize.clean:
        evidence["sanitize"] = {"clean": False, "pattern_id": sanitize.pattern_id}
        return no_ad("injection_detected", "Known prompt injection pattern was rejected before the provider call.")
    estimated = estimate_relevance_tokens(normalized_scene, summaries)
    evidence["context"]["estimated_tokens"] = estimated
    if estimated > context_budget_tokens:
        return no_ad("budget_exceeded", "Context exceeds the disclosed conservative token estimate budget.")
    try:
        raw = client.score(json.loads(json.dumps(normalized_scene)), json.loads(json.dumps(summaries)))
    except TimeoutError:
        return no_ad("llm_timeout", "Relevance provider timed out.")
    except Exception as exc:  # noqa: BLE001 - provider failures cannot bypass the gate
        evidence["provider_error_type"] = type(exc).__name__
        return no_ad("llm_error", "Relevance provider failed; no auction was accepted.")
    # Audit bounded raw advice, never transport headers or credentials.
    evidence["raw_relevance_output"] = raw[:1_048_576] if isinstance(raw, str) else {"invalid_type": type(raw).__name__}
    try:
        scores = parse_relevance_output(raw, evidence["candidate_ids"])
    except RelevanceError:
        return no_ad("llm_output_invalid", "Relevance advice failed the strict closed-set schema.")
    evidence["scores"] = scores
    candidate_bids = {ad.ad_id: valid_bids[ad.ad_id] for ad in eligible}
    try:
        choice = choose_winner(candidate_bids, {ad_id: item["relevance"] for ad_id, item in scores.items()}, budgets)
    except (BidError, ValueError, TypeError):
        return no_ad("auction_invalid", "Auction inputs failed deterministic validation.")
    if choice is None or choice.relevance == 0:
        return no_ad("no_relevant_candidates", "No eligible candidate has positive relevance advice.")
    chosen = next(ad for ad in eligible if ad.ad_id == choice.ad_id)
    verdict = run_compliance(chosen, scene, eligible, banned_words, rules)
    evidence["compliance"] = {"approved": verdict.approved, "executed": True,
                              "results": [asdict(check) for check in verdict.results]}
    evidence["auction_choice"] = asdict(choice)
    if not verdict.approved:
        return no_ad("compliance_rejected", f"Deterministic compliance rejected rule {verdict.rejected_rule()}.")
    before = budgets[choice.ad_id]["remaining_cents"]
    result = {"kind": "ad", "request_id": request_id, "audit_id": audit_id,
              "ad": {"ad_id": chosen.ad_id, "title": chosen.title, "copy": chosen.copy, "category": chosen.category},
              "explanation": _explanation(scores[chosen.ad_id]["reason"], banned_words),
              "auction": {"bid_cents": choice.bid_cents, "relevance": choice.relevance,
                          "score": choice.score, "price_cents": choice.price_cents,
                          "budget_before_cents": before, "budget_after_cents": before - choice.price_cents}}
    if validate_v2_result(result):
        return no_ad("auction_invalid", "Auction result failed the public result contract.")
    try:
        return ledger.finalize(request_id, fingerprint, result, evidence,
                               ad_id=choice.ad_id, charge_cents=choice.price_cents)
    except InsufficientBudget:
        # finalize guarantees the losing transaction rolled back. Never select an
        # automatic alternative after this failure; persist a zero-charge terminal.
        return no_ad("budget_race", "Remaining budget changed before atomic finalization; no alternative was selected.")
    except RequestConflict:
        return {"kind": "no_ad", "request_id": request_id, "audit_id": "",
                "reason_code": "request_conflict", "detail": "request_id was finalized with different inputs; no new charge was attempted."}
    except Exception:  # noqa: BLE001 - audit failure/commit uncertainty is not zero-charge proof
        return _unknown(request_id)
