#!/usr/bin/env python3
"""语义评估门禁（D7 门禁 4）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\check_semantic_eval.py
    .venv\\Scripts\\python.exe scripts\\check_semantic_eval.py --base origin/main
    .venv\\Scripts\\python.exe scripts\\check_semantic_eval.py --files prompts/prompt_v1.0.yaml

课程 §6 门禁 4：
    "Semantic evaluation gate — for any prompt or model change, the pipeline replays
     a fixed evaluation set against quality thresholds before the change can reach
     production; if a threshold fails, the change is blocked and reported."

⚠️ 本门禁当前处于**受限状态**，脚本会如实报告而非伪装通过：
    · 固定评估集 `eval/eval_cases.json` 尚未建立（口径待 OQ-005 定）
    · 仓库当前**没有 prompt 文件**（`prompts/` 为空），触发条件尚不成立

判定（fail-closed）：
    ① 无 prompt/model 变更            → PASS（报告"不适用"，说明触发条件未成立）
    ② 有 prompt/model 变更 + 无评估集 → **FAIL**（阻断，不得无评估即上生产）
    ③ 有 prompt/model 变更 + 有评估集 → 运行评估集 replay，任何阈值未过即 FAIL

退出码：0 = 通过或不适用；1 = 阻断。本脚本只读。
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
    if explicit:
        return sorted(set(explicit))
    if base:
        out = git("diff", "--name-only", f"{base}...HEAD")
        if out.strip():
            return sorted({f for f in out.splitlines() if f.strip()})
    files = [ln[3:].strip() for ln in git("status", "--porcelain").splitlines() if ln.strip()]
    files += [f for f in git("diff", "--name-only", "HEAD~1", "HEAD").splitlines() if f.strip()]
    return sorted({f for f in files if f})


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
    """有评估集时，运行它并按阈值判定。评估集缺失由调用方处理。"""
    errors: list[str] = []
    if not EVAL_RUNNER.exists():
        return ["评估集存在但 eval/eval_runner.py 缺失，无法 replay（阻断）"]
    proc = subprocess.run(
        [sys.executable, str(EVAL_RUNNER)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print("--- eval_runner 输出 ---")
    print(proc.stdout.strip() or "(无输出)")
    if proc.returncode != 0:
        errors.append(f"评估集 replay 未通过（退出码 {proc.returncode}），变更被阻断")
    return errors


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="语义评估门禁（D7 门禁 4）")
    parser.add_argument("--base", help="对比基线（默认自动探测）")
    parser.add_argument("--files", nargs="*", help="显式指定变更文件（本地试验用）")
    args = parser.parse_args(argv[1:])

    base = None if args.files else resolve_base(args.base)
    changed = changed_files(base, args.files)

    prompt_changes = [f for f in changed if PROMPT_RE.match(f)]
    model_change = model_settings_changed(base)

    has_eval = EVAL_CASES.exists()
    if has_eval:
        print(f"评估集 {EVAL_CASES.relative_to(ROOT).as_posix()}: **存在**")
        print("  可随时一键 replay：python eval/eval_runner.py")
    else:
        print(f"评估集 {EVAL_CASES.relative_to(ROOT).as_posix()}: **不存在**")
    print(f"prompt 变更: {prompt_changes or '无'}")
    print(f"model 变更: {'是' if model_change else '否'}")

    if not prompt_changes and not model_change:
        print()
        print("PASS — 不适用：本次变更不含 prompt 或 model 变更，门禁触发条件未成立")
        if has_eval:
            print("  （注：评估集已就位且可一键 replay；ADR-003 未要求每次提交都 replay ——")
            print("   若要改为提交即 replay，属策略变更，须重开 ADR-003）")
        else:
            print("  （注：仓库当前 prompts/ 为空，尚无版本化运行时 prompt）")
        return 0

    print()
    if not has_eval:
        print("FAIL — 检测到 prompt/model 变更，但固定评估集不存在，无法 replay 质量阈值。")
        print("  依据：课程 §6 门禁 4 —— prompt/model 变更须先 replay 固定评估集。")
        print("  处置：先建立 eval/eval_cases.json（≥20 条）与 eval/eval_runner.py，")
        print("        并在 config.yaml 声明质量阈值；否则该变更不得进入 production。")
        return 1

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
