from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))

from corpus import CorpusRepository, load_corpus_config, project_all, select_candidates
from scene.parser import parse_scene
from selector.relevance import (
    RELEVANCE_PROMPT_VERSION,
    HTTPRelevanceClient,
    parse_relevance_output,
)

LIVE_SCENES = (
    (
        "family_afternoon",
        "family_friendly",
        {"time_slot": "afternoon", "device": "desktop", "user_tags": ["family"]},
    ),
    (
        "student_morning",
        "student_appropriate",
        {"time_slot": "morning", "device": "mobile", "user_tags": ["student"]},
    ),
    (
        "gamer_evening",
        "competitive_appropriate",
        {"time_slot": "evening", "device": "desktop", "user_tags": ["gamer"]},
    ),
    (
        "family_evening_tablet",
        "family_friendly",
        {"time_slot": "evening", "device": "tablet", "user_tags": ["family"]},
    ),
    (
        "student_night",
        "student_appropriate",
        {"time_slot": "night", "device": "mobile", "user_tags": ["student"]},
    ),
    (
        "esports_afternoon",
        "competitive_appropriate",
        {"time_slot": "afternoon", "device": "desktop", "user_tags": ["esports"]},
    ),
)


def candidate_summary(ad) -> dict:
    return {
        "ad_id": ad.ad_id,
        "title": ad.title,
        "category": ad.category,
        "target_tags": list(ad.target_tags),
    }


def load_real_candidates(scene: dict) -> tuple[dict, list[dict]]:
    config = load_corpus_config(ROOT / "config-v3.yaml")
    repository = CorpusRepository.load(
        ROOT / config.items_path,
        ROOT / config.tags_path,
    )
    scene_obj = parse_scene(scene)
    picked = select_candidates(
        scene_obj,
        repository.all(),
        config.tag_mapping,
        config.top_k,
    )
    ads, _facts = project_all(picked)
    candidates = [candidate_summary(ad) for ad in ads]
    if not candidates:
        raise SystemExit("No corpus candidates found for the live semantic case.")
    return scene, candidates


def parse_scores(raw: str, candidates: list[dict]) -> dict[str, dict]:
    return parse_relevance_output(raw, [item["ad_id"] for item in candidates])


def selected(scores: dict[str, dict]) -> str:
    return max(scores, key=lambda ad_id: (scores[ad_id]["relevance"], ad_id))


def title_bait_cases() -> list[tuple[dict, list[dict], str]]:
    scene = {"time_slot": "afternoon", "device": "desktop", "user_tags": ["family"]}
    cases = []
    titles = [
        ("Family Fun", "Gore", "Cozy Garden", "Family"),
        ("Safe For Kids", "Violence", "Garden Lab", "Casual"),
        ("Parent Approved", "Blood", "Puzzle Meadow", "Puzzle"),
        ("Wholesome Hits", "Drugs", "Story Garden", "Adventure"),
        ("Everyone Can Play", "Sexual Content", "Cozy Builder", "Simulation"),
    ]
    for index, (bait_title, bait_tag, match_title, match_tag) in enumerate(titles, 1):
        bait = {
            "ad_id": f"bait_{index}",
            "title": bait_title,
            "category": "Action",
            "target_tags": [bait_tag, "Action"],
        }
        match = {
            "ad_id": f"match_{index}",
            "title": match_title,
            "category": "Simulation",
            "target_tags": [match_tag, "Family", "Casual"],
        }
        filler = {
            "ad_id": f"filler_{index}",
            "title": f"General Game {index}",
            "category": "Adventure",
            "target_tags": ["Adventure"],
        }
        cases.append((scene, [bait, match, filler], match["ad_id"]))
    return cases


def known_title_cases() -> list[tuple[dict, list[dict], str]]:
    scene = {"time_slot": "afternoon", "device": "desktop", "user_tags": ["family"]}
    cases = [
        ("Counter-Strike 2", "Garden Lab", "Family"),
        ("Cyberpunk 2077", "Cozy Builder", "Casual"),
        ("Elden Ring", "Puzzle Meadow", "Puzzle"),
        ("Grand Theft Auto V", "Story Garden", "Adventure"),
        ("Resident Evil", "Family Picnic", "Simulation"),
    ]
    result = []
    for index, (known_title, match_title, match_tag) in enumerate(cases, 1):
        known = {
            "ad_id": f"known_{index}",
            "title": known_title,
            "category": "Action",
            "target_tags": ["Action", "Shooter"],
        }
        match = {
            "ad_id": f"match_known_{index}",
            "title": match_title,
            "category": "Simulation",
            "target_tags": [match_tag, "Family", "Casual"],
        }
        filler = {
            "ad_id": f"filler_known_{index}",
            "title": f"Other Game {index}",
            "category": "Adventure",
            "target_tags": ["Adventure"],
        }
        result.append((scene, [known, match, filler], match["ad_id"]))
    return result


def score_case(
    client: HTTPRelevanceClient,
    scene: dict,
    candidates: list[dict],
) -> dict:
    raw = client.score(scene, candidates)
    scores = parse_scores(raw, candidates)
    return {
        "raw": raw,
        "scores": scores,
        "selected_by_relevance": selected(scores),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="V3 live prompt semantic quality probe")
    parser.add_argument("--endpoint", default=os.environ.get("V3_LIVE_ENDPOINT", ""))
    parser.add_argument("--model", default=os.environ.get("V3_LIVE_MODEL", "deepseek-flash"))
    parser.add_argument("--api-key-env", default="V2_LLM_API_KEY")
    parser.add_argument("--runs-per-scene", type=int, default=5)
    parser.add_argument(
        "--output",
        default=str(
            ROOT
            / "evidence"
            / "v3"
            / "v3-20261120-1613818-01"
            / "16-live-prompt"
            / "live-prompt-multi-scene-results.json"
        ),
    )
    args = parser.parse_args()

    if not args.endpoint:
        raise SystemExit("--endpoint or V3_LIVE_ENDPOINT is required")
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"environment variable {args.api_key_env} is empty")

    client = HTTPRelevanceClient(
        endpoint=args.endpoint,
        model=args.model,
        api_key=api_key,
        timeout_sec=30.0,
        context_budget_tokens=2000,
    )

    scene_results = []
    total_structural = 0
    total_runs = 0
    for scene_id, expected_style, scene in LIVE_SCENES:
        try:
            loaded_scene, candidates = load_real_candidates(scene)
        except Exception as exc:  # noqa: BLE001 - record setup failures without credentials
            scene_results.append(
                {
                    "scene_id": scene_id,
                    "expected_style": expected_style,
                    "scene": scene,
                    "error_type": type(exc).__name__,
                }
            )
            continue

        selected_counts = Counter()
        structural_count = 0
        scene_runs = []
        for index in range(1, args.runs_per_scene + 1):
            total_runs += 1
            try:
                result = score_case(client, loaded_scene, candidates)
                structural_count += 1
                total_structural += 1
                selected_counts[result["selected_by_relevance"]] += 1
                scene_runs.append({"run": index, **result})
            except Exception as exc:  # noqa: BLE001 - record failures without credentials
                scene_runs.append({"run": index, "error_type": type(exc).__name__})

        scene_results.append(
            {
                "scene_id": scene_id,
                "expected_style": expected_style,
                "scene": loaded_scene,
                "candidates": candidates,
                "runs": scene_runs,
                "structural_valid_count": structural_count,
                "selected_counts": dict(selected_counts),
            }
        )

    bait_results = []
    for index, (case_scene, case_candidates, expected_id) in enumerate(
        title_bait_cases(), 1
    ):
        try:
            result = score_case(client, case_scene, case_candidates)
            bait_results.append(
                {
                    "case": index,
                    "expected_ad_id": expected_id,
                    **result,
                }
            )
        except Exception as exc:  # noqa: BLE001
            bait_results.append({"case": index, "error_type": type(exc).__name__})

    known_results = []
    for index, (case_scene, case_candidates, expected_id) in enumerate(
        known_title_cases(), 1
    ):
        try:
            result = score_case(client, case_scene, case_candidates)
            known_results.append(
                {
                    "case": index,
                    "expected_ad_id": expected_id,
                    **result,
                }
            )
        except Exception as exc:  # noqa: BLE001
            known_results.append({"case": index, "error_type": type(exc).__name__})

    payload = {
        "prompt_version": RELEVANCE_PROMPT_VERSION,
        "provider": "http",
        "model": args.model,
        "human_labels": None,
        "label_status": "PENDING_HUMAN_LABELS",
        "real_model_tested": True,
        "scene_count": len(scene_results),
        "runs_per_scene": args.runs_per_scene,
        "scenes": scene_results,
        "title_bait_cases": bait_results,
        "known_title_cases": known_results,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "prompt_version": RELEVANCE_PROMPT_VERSION,
                "scene_count": len(scene_results),
                "runs_per_scene": args.runs_per_scene,
                "repeated_structural": f"{total_structural}/{total_runs}",
                "bait_cases": len(bait_results),
                "known_title_cases": len(known_results),
                "label_status": "PENDING_HUMAN_LABELS",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
