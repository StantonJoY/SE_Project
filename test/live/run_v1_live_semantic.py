from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))

from ads.banned_words import BannedWords
from app.cli import load_corpus_context
from app.config import AppConfig, LLMConfig
from app.pipeline import recommend
from audit import JsonlAuditStore
from compliance.rules import SceneRules
from render import to_json
from selector import LLMUnavailable

SCENES = (
    ("family_afternoon", {"time_slot": "afternoon", "device": "desktop", "user_tags": ["family"]}),
    ("student_morning", {"time_slot": "morning", "device": "mobile", "user_tags": ["student"]}),
    ("gamer_evening", {"time_slot": "evening", "device": "desktop", "user_tags": ["gamer"]}),
    ("family_evening_tablet", {"time_slot": "evening", "device": "tablet", "user_tags": ["family"]}),
    ("student_night", {"time_slot": "night", "device": "mobile", "user_tags": ["student"]}),
    ("esports_afternoon", {"time_slot": "afternoon", "device": "desktop", "user_tags": ["esports"]}),
)


class HTTPSelectorClient:
    """Test-only V1 LLMClient over an OpenAI-compatible chat endpoint."""

    def __init__(self, endpoint: str, model: str, api_key: str, timeout_sec: float = 30.0) -> None:
        self.endpoint = endpoint
        self.model = model
        self._api_key = api_key
        self.timeout_sec = timeout_sec

    def select(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                envelope = json.loads(response.read().decode("utf-8"))
            content = envelope["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("provider content is not text")
            return content
        except (urllib.error.URLError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            raise LLMUnavailable(f"HTTP selector provider failed ({type(exc).__name__})") from None


def result_payload(rec) -> dict:
    text = to_json(rec.result)
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="V1 live semantic quality probe")
    parser.add_argument("--endpoint", default=os.environ.get("V3_LIVE_ENDPOINT", ""))
    parser.add_argument("--model", default=os.environ.get("V3_LIVE_MODEL", "deepseek-flash"))
    parser.add_argument("--api-key-env", default="V2_LLM_API_KEY")
    parser.add_argument("--runs-per-scene", type=int, default=3)
    parser.add_argument(
        "--output",
        default=str(
            ROOT
            / "evidence"
            / "v3"
            / "v3-20261120-1613818-01"
            / "16-v1-live-prompt"
            / "v1-live-semantic-results.json"
        ),
    )
    args = parser.parse_args()

    if not args.endpoint:
        raise SystemExit("--endpoint or V3_LIVE_ENDPOINT is required")
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"environment variable {args.api_key_env} is empty")

    base_config = AppConfig.load(ROOT / "config.yaml")
    config = replace(
        base_config,
        llm=LLMConfig(
            provider="openai_compatible",
            timeout_sec=30.0,
            model=args.model,
            api_key_env=args.api_key_env,
        ),
        source_path=str(ROOT / "config.yaml"),
    )
    banned = BannedWords.load(ROOT / base_config.data.banned_words_path)
    rules = SceneRules.load(ROOT / base_config.data.scene_rules_path)
    client = HTTPSelectorClient(args.endpoint, args.model, api_key)

    output = Path(args.output)
    audit_path = output.with_name("v1-live.audit.jsonl")
    audit_store = JsonlAuditStore(audit_path)
    results = []

    for scene_id, scene in SCENES:
        try:
            context = load_corpus_context(scene, ROOT / "config.yaml", ROOT, all_items=False)
            run_results = []
            for run in range(1, args.runs_per_scene + 1):
                try:
                    rec = recommend(
                        scene,
                        repo=context.repository,
                        banned_words=banned,
                        rules=rules,
                        client=client,
                        audit_store=audit_store,
                        config=config,
                        content_policy=context.policy,
                    )
                    run_results.append(
                        {
                            "run": run,
                            "audit_id": rec.audit_id,
                            **result_payload(rec),
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - tests record fail-closed outcomes
                    run_results.append({"run": run, "error_type": type(exc).__name__})
            results.append(
                {
                    "scene_id": scene_id,
                    "scene": scene,
                    "candidate_count": context.repository.count,
                    "runs": run_results,
                }
            )
        except Exception as exc:  # noqa: BLE001 - setup failure is evidence
            results.append({"scene_id": scene_id, "scene": scene, "error_type": type(exc).__name__})

    payload = {
        "prompt_version": "ctx-v1.1",
        "provider": "http",
        "model": args.model,
        "real_model_tested": True,
        "human_labels": None,
        "label_status": "PENDING_HUMAN_LABELS",
        "v1_live_note": (
            "This is a test-only LLMClient injection through app.pipeline.recommend; "
            "the product V1 CLI still uses MockLLM."
        ),
        "scenes": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    structural = sum(
        len([run for run in scene.get("runs", []) if "kind" in run])
        for scene in results
    )
    total = len(results) * args.runs_per_scene
    print(
        json.dumps(
            {
                "output": str(output),
                "prompt_version": "ctx-v1.1",
                "scene_count": len(results),
                "runs_per_scene": args.runs_per_scene,
                "structural_valid": f"{structural}/{total}",
                "label_status": "PENDING_HUMAN_LABELS",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
