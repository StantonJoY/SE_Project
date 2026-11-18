from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from app.pipeline_v2 import recommend_v2
from bidding import Ledger, validate_bids
from compliance.rules import SceneRules
from render.schema_v2 import validate_v2_result
from selector.relevance import HTTPRelevanceClient

SAMPLE_COUNT = 20
SCENE = {"time_slot": "morning", "device": "mobile", "user_tags": ["student"]}
HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "live-p95.sqlite3"
CONFIG_PATH = ROOT / "config-v2.yaml"

endpoint = os.environ.get("LIVE_ENDPOINT", "").strip()
model = os.environ.get("LIVE_MODEL", "").strip()
api_key = os.environ.get("V2_LLM_API_KEY", "").strip()

if not endpoint or not model or not api_key:
    raise SystemExit("LIVE_ENDPOINT, LIVE_MODEL and V2_LLM_API_KEY must be set")
if DB_PATH.exists():
    raise SystemExit(f"refusing to overwrite existing database: {DB_PATH}")

usage_sink: list[dict] = []


class CapturingResponse:
    def __init__(self, response):
        self._response = response
        self._buffer = bytearray()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            envelope = json.loads(self._buffer.decode("utf-8"))
            usage = envelope.get("usage")
            usage_sink.append(usage if isinstance(usage, dict) else {})
        except Exception:
            usage_sink.append({"usage_error": "response_not_json"})
        finally:
            self._response.close()
        return False

    def read(self, n=-1):
        chunk = self._response.read(n)
        self._buffer.extend(chunk)
        return chunk

    def read1(self, n=-1):
        reader = getattr(self._response, "read1", None)
        chunk = reader(n) if reader else self._response.read(n)
        self._buffer.extend(chunk)
        return chunk


def capturing_transport(req, timeout=None):
    return CapturingResponse(urllib.request.urlopen(req, timeout=timeout))


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(p * len(ordered)) - 1)
    return ordered[index]


def usage_numbers(usage: dict) -> tuple[int, int, int]:
    hit = int(usage.get("prompt_cache_hit_tokens", 0) or 0)
    miss = int(usage.get("prompt_cache_miss_tokens", 0) or 0)
    prompt = int(usage.get("prompt_tokens", 0) or 0)
    completion = int(usage.get("completion_tokens", 0) or 0)
    if hit == 0 and miss == 0:
        miss = prompt
    return hit, miss, completion


config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
threshold = float(config["replay"]["latency_p95_threshold_sec"])

repo = AdRepository.load(ROOT / "data" / "ads.json")
banned = BannedWords.load(ROOT / "data" / "banned_words.json")
rules = SceneRules.load(ROOT / "data" / "scene_rules.json")
raw_bids = json.loads((ROOT / "data" / "bids-v2.json").read_text(encoding="utf-8"))
for bid in raw_bids:
    bid["budget_cents"] = 100_000_000
bids = validate_bids(raw_bids, known_ad_ids={ad.ad_id for ad in repo.all()})

client = HTTPRelevanceClient(
    endpoint=endpoint,
    model=model,
    api_key=api_key,
    timeout_sec=30,
    transport=capturing_transport,
    context_budget_tokens=2000,
)
provider = f"http:{model}"
samples: list[dict] = []

with Ledger(str(DB_PATH)) as ledger:
    ledger.seed(bids)

    for index in range(1, SAMPLE_COUNT + 1):
        request_id = f"v2-live-p95-{index:02d}"
        usage_sink.clear()
        started = time.perf_counter()
        result = recommend_v2(
            SCENE,
            request_id=request_id,
            repo=repo,
            bids=bids,
            client=client,
            ledger=ledger,
            banned_words=banned,
            rules=rules,
            model_version=provider,
            policy_version="pay-as-bid-v1",
            context_budget_tokens=2000,
        )
        elapsed = time.perf_counter() - started
        usage = usage_sink[0] if usage_sink else {}
        hit, miss, completion = usage_numbers(usage)
        peak_cost = hit * 0.04 / 1_000_000 + miss * 2 / 1_000_000 + completion * 8 / 1_000_000
        offpeak_cost = hit * 0.02 / 1_000_000 + miss * 1 / 1_000_000 + completion * 4 / 1_000_000
        schema_errors = validate_v2_result(result)
        auction = result.get("auction") or {}
        sample = {
            "index": index,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_sec": elapsed,
            "kind": result.get("kind"),
            "reason_code": result.get("reason_code"),
            "ad_id": (result.get("ad") or {}).get("ad_id"),
            "relevance": auction.get("relevance"),
            "price_cents": auction.get("price_cents"),
            "schema_errors": schema_errors,
            "usage_present": bool(usage) and "usage_error" not in usage,
            "prompt_cache_hit_tokens": hit,
            "prompt_cache_miss_tokens": miss,
            "completion_tokens": completion,
            "peak_cost_cny": peak_cost,
            "offpeak_cost_cny": offpeak_cost,
        }
        samples.append(sample)
        print(f"sample {index}/{SAMPLE_COUNT}: {sample['kind']} {sample['ad_id'] or '-'} {elapsed:.3f}s", file=sys.stderr)

    final_budgets = ledger.budgets()

latencies = [row["duration_sec"] for row in samples]
successes = [row for row in samples if row["kind"] == "ad" and not row["schema_errors"]]
structural_ok = [row for row in samples if not row["schema_errors"] and row["usage_present"]]
p50 = percentile(latencies, 0.50)
p95 = percentile(latencies, 0.95)
max_latency = max(latencies) if latencies else None
functional_rate = len(successes) / len(samples) if samples else 0.0

report = {
    "provider": provider,
    "endpoint_path": urlsplit(endpoint).path,
    "sample_count": len(samples),
    "threshold_sec": threshold,
    "functional_ad_count": len(successes),
    "functional_success_rate": functional_rate,
    "structural_success_count": len(structural_ok),
    "schema_failure_count": sum(1 for row in samples if row["schema_errors"]),
    "usage_success_count": sum(1 for row in samples if row["usage_present"]),
    "p50_sec": p50,
    "p95_sec": p95,
    "max_sec": max_latency,
    "p95_pass": p95 is not None and p95 <= threshold,
    "prompt_cache_hit_tokens": sum(row["prompt_cache_hit_tokens"] for row in samples),
    "prompt_cache_miss_tokens": sum(row["prompt_cache_miss_tokens"] for row in samples),
    "completion_tokens": sum(row["completion_tokens"] for row in samples),
    "peak_cost_cny": sum(row["peak_cost_cny"] for row in samples),
    "offpeak_cost_cny": sum(row["offpeak_cost_cny"] for row in samples),
    "functional_pass": functional_rate >= 0.95,
    "semantic_quality": "PENDING_HUMAN_LABELS",
    "final_budgets": final_budgets,
    "samples": samples,
}

print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))

passed = (
    report["usage_success_count"] == report["sample_count"]
    and report["schema_failure_count"] == 0
    and report["functional_pass"]
    and report["p95_pass"]
)
raise SystemExit(0 if passed else 1)