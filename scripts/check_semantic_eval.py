#!/usr/bin/env python3
"""Gate 4: replay BOTH fixed V1 and V2 suites for semantic changes.

Runtime prompts live in Python. Auction code, bids and policy configuration
also affect decisions and trigger replay. This gate never invokes a live API.
ADR-005 / REQ-ADS-GOV-003; INV-V2-012.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_CASES = ROOT / "eval" / "eval_cases.json"
EVAL_RUNNER = ROOT / "eval" / "eval_runner.py"
CONFIG = ROOT / "config.yaml"

# 触发门禁的文件类别（课程原文："for any prompt or model change"）
PROMPT_RE = re.compile(r"^(prompts/.*|.*\.prompt\.(md|ya?ml))$")
MODEL_KEYS = ("model", "provider")
V2_EVAL_CASES = ROOT / "eval" / "v2_cases.json"
V2_EVAL_RUNNER = ROOT / "eval" / "v2_runner.py"


def semantic_changes(changed: list[str]) -> list[str]:
    """Actual executable prompt/policy sources, including embedded Python prompts."""
    exact = {"config.yaml", "config-v2.yaml", "data/bids-v2.json",
             "src/selector/relevance.py", "src/selector/context.py", "src/selector/client.py",
             "src/app/pipeline.py", "src/app/pipeline_v2.py", "src/app/cli_v2.py",
             "eval/eval_cases.json", "eval/eval_runner.py", "eval/v2_cases.json", "eval/v2_runner.py"}
    return sorted(f for f in changed if f in exact or f.startswith("src/bidding/") or PROMPT_RE.match(f))


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc.stdout if proc.returncode == 0 else ""


def resolve_base(explicit: str | None) -> str | None:
    for cand in ([explicit] if explicit else []) + ["origin/main", "origin/HEAD", "main", "HEAD~1"]:
        if cand and git("rev-parse", "--verify", "--quiet", f"{cand}^{{commit}}").strip():
            return cand
    return None


def changed_files(base: str | None, explicit: list[str] | None) -> list[str]:
    """Include committed, unstaged, staged and individually named untracked files."""
    if explicit is not None:
        return sorted(set(explicit))
    files = git("diff", "--name-only", f"{base}...HEAD").splitlines() if base else []
    files += git("diff", "--name-only", "HEAD").splitlines()
    files += git("ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({f for f in files if f.strip()})


def model_settings_changed(base: str | None) -> bool:
    """config.yaml 的 model/provider 是否变化 —— 即"model change"。"""
    if not CONFIG.exists():
        return False
    if not base:
        return False
    diff = git("diff", f"{base}...HEAD", "--", "config.yaml")
    if not diff.strip():
        return False
    return any(re.search(rf"^[+-].*\b{k}\b", diff, re.M) for k in MODEL_KEYS)


def threshold_check() -> list[str]:
    """Missing runner, missing cases or any failed threshold blocks."""
    errors: list[str] = []
    for cases, runner in ((EVAL_CASES, EVAL_RUNNER), (V2_EVAL_CASES, V2_EVAL_RUNNER)):
        if not cases.is_file() or not runner.is_file():
            errors.append(f"Missing fixed evaluation asset: {cases.name} / {runner.name}")
            continue
        proc = subprocess.run([sys.executable, str(runner), "--no-write"], cwd=ROOT,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"--- {runner.name} ---")
        print(proc.stdout.strip() or "(no stdout)")
        if proc.returncode:
            print(proc.stderr.strip())
            errors.append(f"{runner.name} failed (exit {proc.returncode}); change blocked")
    return errors


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="语义评估门禁（D7 门禁 4）")
    parser.add_argument("--base", help="对比基线（默认自动探测）")
    parser.add_argument("--files", nargs="*", help="显式指定变更文件（本地试验用）")
    args = parser.parse_args(argv[1:])

    base = None if args.files else resolve_base(args.base)
    changed = changed_files(base, args.files)

    triggers = semantic_changes(changed)
    print(f"Semantic changes: {triggers}")
    if not triggers and not model_settings_changed(base):
        print("PASS — no semantic prompt/model/auction changes")
        return 0

    errors = threshold_check()
    if errors:
        print()
        print(f"FAIL — 语义评估门禁未通过，共 {len(errors)} 项：")
        for e in errors:
            print(f"  - {e}")
        return 1

    print()
    print("PASS — prompt/model 变更已通过固定评估集 replay 与质量阈值")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
