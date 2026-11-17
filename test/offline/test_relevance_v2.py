"""V2 relevance protocol tests based only on its public schema.

REQ-ADS-ARCH-012; REQ-ADS-NFR-SAFETY-007; REQ-ADS-NFR-QA-003;
INV-ADS-002/003. Negative tests preserve the advisory AI authority boundary.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from selector.relevance import FixedRelevanceClient, RelevanceError, parse_relevance_output


def _score(ad_id="a", relevance=90, reason="Matches this scene"):
    return {"ad_id": ad_id, "relevance": relevance, "reason": reason}


def _raw(*scores, **extras):
    return json.dumps({"scores": list(scores), **extras}, ensure_ascii=False)


def test_relevance_parses_exact_closed_set_at_inclusive_bounds():
    """REQ-ADS-ARCH-012: AI controls only each closed-set relevance and its reason."""
    raw = _raw(_score("b", 100, "最高相关"), _score("a", 0, "不相关"))
    assert parse_relevance_output(raw, ["a", "b"]) == {
        "a": {"relevance": 0, "reason": "不相关"},
        "b": {"relevance": 100, "reason": "最高相关"},
    }


@pytest.mark.parametrize("relevance", [True, False, -1, 101, 90.0, "90", None, float("nan"), float("inf"), -float("inf")])
def test_reject_noninteger_nonfinite_out_of_range_relevance(relevance):
    """REQ-ADS-NFR-SAFETY-007, INV-ADS-003: negative test forbids anomalous AI numbers."""
    with pytest.raises(RelevanceError):
        parse_relevance_output(_raw(_score(relevance=relevance)), ["a"])


@pytest.mark.parametrize("raw", [
    "", "not JSON", "```json\n{\"scores\": []}\n```", "null", "[]", "{}",
    '{"scores":null}', '{"scores":{}}', '{"scores":[]}',
    '{"scores":[{"ad_id":"a","relevance":90}]}',
    '{"scores":[{"ad_id":"a","reason":"match"}]}',
    '{"scores":[{"relevance":90,"reason":"match"}]}',
    '{"scores":[null]}', '{"scores":[42]}',
])
def test_reject_missing_and_malformed_output(raw):
    """INV-ADS-003, REQ-ADS-ARCH-012: negative test rejects incomplete schema and wrappers."""
    with pytest.raises(RelevanceError):
        parse_relevance_output(raw, ["a"])


@pytest.mark.parametrize("reason", [None, True, 1, [], {}])
def test_reason_is_strictly_a_string(reason):
    """REQ-ADS-ARCH-012, INV-ADS-003: negative test validates explanation type."""
    with pytest.raises(RelevanceError):
        parse_relevance_output(_raw(_score(reason=reason)), ["a"])


@pytest.mark.parametrize("scores", [
    [_score("a"), _score("a")],
    [_score("a")],
    [_score("a"), _score("foreign")],
    [_score("a"), _score("b"), _score("foreign")],
])
def test_reject_duplicate_missing_or_foreign_candidates(scores):
    """INV-ADS-002/003, REQ-ADS-ARCH-012: negative test requires exactly one score per candidate."""
    with pytest.raises(RelevanceError):
        parse_relevance_output(_raw(*scores), ["a", "b"])


@pytest.mark.parametrize("field", ["price_cents", "charge_cents", "spent_cents", "bid_cents", "budget_cents", "winner", "extra"])
@pytest.mark.parametrize("location", ["root", "score"])
def test_ai_cannot_write_economic_fields_or_extra_keys(field, location):
    """REQ-ADS-ARCH-012: negative test enforces no AI authority over price, spend, or winner."""
    score = _score()
    if location == "score":
        score[field] = 1
        raw = _raw(score)
    else:
        raw = _raw(score, **{field: 1})
    with pytest.raises(RelevanceError):
        parse_relevance_output(raw, ["a"])


def test_nonfinite_values_cannot_hide_in_extra_fields():
    """REQ-ADS-NFR-SAFETY-007, REQ-ADS-ARCH-012: negative test rejects nonstandard JSON constants."""
    for constant in ("NaN", "Infinity", "-Infinity"):
        raw = '{"scores":[{"ad_id":"a","relevance":90,"reason":"match"}],"hidden":' + constant + "}"
        with pytest.raises(RelevanceError):
            parse_relevance_output(raw, ["a"])


def test_fixed_provider_is_deterministic_and_scores_only_requested_candidates():
    """REQ-ADS-NFR-QA-003, REQ-ADS-ARCH-012: offline provider emits the same closed-set advice."""
    scene = {"time_slot": "night", "device": "mobile", "user_tags": ["student"]}
    candidates = [
        {"ad_id": "a", "title": "Coffee", "category": "food_delivery", "target_tags": ["student"]},
        {"ad_id": "b", "title": "Course", "category": "education", "target_tags": ["student"]},
    ]
    client = FixedRelevanceClient({"a": 90, "b": 50, "foreign": 100})
    first = client.score(scene, candidates)
    assert first == client.score(scene, candidates)
    parsed = parse_relevance_output(first, ["a", "b"])
    assert {key: value["relevance"] for key, value in parsed.items()} == {"a": 90, "b": 50}
    assert all(isinstance(value["reason"], str) for value in parsed.values())
