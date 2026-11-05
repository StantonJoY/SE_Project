"""V2 startup configuration, durable ledger and provider wiring.

Implements: ADR-005 (separate V2 entry point; preserves V1 behavior).
Verifies: REQ-ADS-NFR-SAFETY-006, REQ-ADS-ARCH-010/012, REQ-ADS-FR-006/008.
Only this startup layer reads credentials; they are never passed to audit evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import yaml

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from app.pipeline_v2 import recommend_v2
from bidding import Ledger, validate_bids
from compliance.rules import SceneRules
from render.schema_v2 import validate_v2_result
from selector.relevance import FixedRelevanceClient, HTTPRelevanceClient, RelevanceClient

DEFAULT_CONFIG = "config-v2.yaml"


def _keys(value: object, expected: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{name} has missing or extra configuration fields")
    return value


def load_v2_config(path: str | Path) -> dict:
    """Fail loudly at startup; pricing/formula identifiers select one audited policy."""
    with Path(path).open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    config = _keys(value, {"model", "prompt", "paths", "policy", "replay"}, "config")
    model = _keys(config["model"], {"provider", "version", "name", "endpoint", "api_key_env", "timeout_sec", "fixed_scores"}, "model")
    if model["provider"] not in {"fixed", "http"}:
        raise ValueError("model.provider must be fixed or http")
    for key in ("version", "name", "endpoint", "api_key_env"):
        if not isinstance(model[key], str) or (key in {"version", "api_key_env"} and not model[key].strip()):
            raise ValueError(f"model.{key} must be an appropriate string")
    timeout = model["timeout_sec"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise ValueError("model.timeout_sec must be finite and within (0, 120]")
    if not isinstance(model["fixed_scores"], dict) or any(
        not isinstance(k, str) or type(v) is not int or not 0 <= v <= 100 for k, v in model["fixed_scores"].items()
    ):
        raise ValueError("model.fixed_scores must map IDs to integers within 0..100")
    prompt = _keys(config["prompt"], {"context_budget_tokens"}, "prompt")
    if type(prompt["context_budget_tokens"]) is not int or not 0 < prompt["context_budget_tokens"] <= 2000:
        raise ValueError("context_budget_tokens must be within 1..2000")
    paths = _keys(config["paths"], {"ads", "bids", "banned_words", "scene_rules", "ledger"}, "paths")
    if any(not isinstance(p, str) or not p.strip() for p in paths.values()):
        raise ValueError("all paths must be nonempty strings")
    policy = _keys(config["policy"], {"version", "score_formula", "pricing", "tie_break"}, "policy")
    if policy != {"version": "pay-as-bid-v1", "score_formula": "relevance_times_bid",
                  "pricing": "pay_as_bid", "tie_break": "ad_id_ascending"}:
        raise ValueError("unsupported auction policy; an architecture change and replay are required")
    replay = _keys(config["replay"], {"pass_rate_threshold", "compliance_escape_limit", "latency_p95_threshold_sec"}, "replay")
    for key, lower, upper in (("pass_rate_threshold", 0, 1), ("latency_p95_threshold_sec", 0, 120)):
        number = replay[key]
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or not lower < number <= upper:
            raise ValueError(f"invalid replay.{key}")
    if type(replay["compliance_escape_limit"]) is not int or replay["compliance_escape_limit"] != 0:
        raise ValueError("compliance_escape_limit must be exactly zero")
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli_v2", description="V2 deterministic pay-as-bid recommendation")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--request-id", required=True)
    scene = parser.add_mutually_exclusive_group()
    scene.add_argument("--scene", help="JSON scene object")
    scene.add_argument("--time-slot")
    parser.add_argument("--device")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--db", help="persistent SQLite ledger path")
    parser.add_argument("--bids", "--bids-file", dest="bids")
    parser.add_argument("--provider", choices=("fixed", "http"))
    parser.add_argument("--model")
    parser.add_argument("--base-url", help="HTTP API root; /chat/completions is appended")
    parser.add_argument("--endpoint", help="complete chat-completions HTTP URL")
    parser.add_argument("--api-key-env", "--key-env", dest="api_key_env", help="environment variable containing the HTTP API key")
    parser.add_argument("--indent", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    try:
        config = load_v2_config(config_path)
        source = config_path.parent
        paths, model, policy = config["paths"], config["model"], config["policy"]
        repo = AdRepository.load(source / paths["ads"])
        banned = BannedWords.load(source / paths["banned_words"])
        rules = SceneRules.load(source / paths["scene_rules"])
        bids_path = Path(args.bids) if args.bids else source / paths["bids"]
        with bids_path.open(encoding="utf-8") as stream:
            bids = validate_bids(json.load(stream), known_ad_ids={ad.ad_id for ad in repo.all()})
        if args.scene is not None:
            raw_scene = json.loads(args.scene)
        else:
            raw_scene = {"time_slot": args.time_slot, "device": args.device, "user_tags": args.tag}
        provider = args.provider or model["provider"]
        client: RelevanceClient
        if provider == "fixed":
            client = FixedRelevanceClient(model["fixed_scores"])
            model_version = model["version"]
        else:
            api_key = os.environ.get(args.api_key_env or model["api_key_env"], "")
            kwargs = {"model": args.model or model["name"], "api_key": api_key,
                      "timeout_sec": model["timeout_sec"],
                      "context_budget_tokens": config["prompt"]["context_budget_tokens"]}
            if args.base_url:
                client = HTTPRelevanceClient(base_url=args.base_url, **kwargs)
            else:
                client = HTTPRelevanceClient(endpoint=args.endpoint or model["endpoint"], **kwargs)
            model_version = f"http:{args.model or model['name']}"
        db = Path(args.db) if args.db else source / paths["ledger"]
        if str(db) != ":memory:":
            db.parent.mkdir(parents=True, exist_ok=True)
        with Ledger(str(db)) as ledger:
            ledger.seed(bids)  # Idempotent initialization; never resets durable spending.
            result = recommend_v2(raw_scene, request_id=args.request_id, repo=repo, bids=bids, client=client,
                                  ledger=ledger, banned_words=banned, rules=rules, model_version=model_version,
                                  policy_version=policy["version"], context_budget_tokens=config["prompt"]["context_budget_tokens"])
        errors = validate_v2_result(result)
        if errors:
            raise ValueError("V2 result contract: " + "; ".join(errors))
    except Exception as exc:  # noqa: BLE001 - startup failures must be visible on stderr
        # Provider configuration errors are already scrubbed; never display credential values.
        print(f"V2 startup/request failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=args.indent or None))
    if result["kind"] == "status_unknown":
        print("Storage status unknown; retry the same request_id and identical inputs.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
