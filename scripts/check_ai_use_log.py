#!/usr/bin/env python3
"""AI-use 日志门禁（D7 门禁 6）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\check_ai_use_log.py
    .venv\\Scripts\\python.exe scripts\\check_ai_use_log.py --base origin/main
    .venv\\Scripts\\python.exe scripts\\check_ai_use_log.py --files src/app/pipeline.py

课程 §6 门禁 6：
    "a pull request that changes code or prompts without updating the AI-use log
     is blocked."

判定逻辑（两层）：
  ① **结构层**：`docs/ai-use-log.yaml` 必须存在、可按 schema 解析、
     每条 entry 含必需字段（id/date/agent/tool/task/artifacts/outcome），
     且 id 唯一、artifacts 非空。
  ② **时效层**：若变更集包含"代码或 prompt"文件，则本日志必须**同时**被修改
     （即出现在同一变更集中）。否则阻断 —— 这正是门禁 6 的原文要求。

变更集来源与 `check_safety_paths.py` 一致：优先 `git diff <base>...HEAD`，
退化到未提交变更 + 最近一次提交。

退出码：0 = 通过；1 = 阻断。本脚本只读。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "docs" / "ai-use-log.yaml"

# 触发门禁的文件类别：代码与 prompt（课程原文 "changes code or prompts"）
CODE_OR_PROMPT_RE = re.compile(
    r"^(src/.*\.py|scripts/.*\.py|test/.*\.py|prompts/.*|.*\.prompt\.md|.*\.prompt\.ya?ml)$"
)
LOG_REL = "docs/ai-use-log.yaml"

REQUIRED_FIELDS = ("id", "date", "agent", "tool", "role", "task", "artifacts", "outcome")
VALID_OUTCOMES = {"accepted", "rejected", "revised", "pending"}
VALID_ROLES = {"plan", "build", "verify", "test", "review"}


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc.stdout if proc.returncode == 0 else ""


def resolve_base(explicit: str | None) -> str | None:
    candidates = [explicit] if explicit else []
    candidates += ["origin/main", "origin/HEAD", "main", "HEAD~1"]
    for cand in candidates:
        if not cand:
            continue
        if git("rev-parse", "--verify", "--quiet", f"{cand}^{{commit}}").strip():
            return cand
    return None


def changed_files(base: str | None, explicit: list[str] | None) -> list[str]:
    if explicit:
        return sorted(set(explicit))
    if base:
        out = git("diff", "--name-only", f"{base}...HEAD")
        if out.strip():
            return sorted({f for f in out.splitlines() if f.strip()})
    files = [line[3:].strip() for line in git("status", "--porcelain").splitlines() if line.strip()]
    files += [f for f in git("diff", "--name-only", "HEAD~1", "HEAD").splitlines() if f.strip()]
    return sorted({f for f in files if f})


def check_structure() -> list[str]:
    errors: list[str] = []
    if not LOG_PATH.exists():
        return [f"AI-use 日志不存在: {LOG_REL}"]

    data = yaml.safe_load(LOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return [f"{LOG_REL} 顶层必须是对象"]

    entries = data.get("entries") or []
    if not entries:
        return [f"{LOG_REL} 的 entries 为空 —— 无记录即无证据"]

    seen: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            errors.append(f"entries[{i}] 不是对象")
            continue
        eid = e.get("id", f"entries[{i}]")
        for f in REQUIRED_FIELDS:
            if f not in e or e[f] in (None, "", []):
                errors.append(f"{eid}: 缺必需字段 {f!r}")
        if eid in seen:
            errors.append(f"{eid}: id 重复")
        seen.add(eid)
        if e.get("outcome") and e["outcome"] not in VALID_OUTCOMES:
            errors.append(f"{eid}: outcome={e['outcome']!r} 不在 {sorted(VALID_OUTCOMES)}")
        if e.get("role") and e["role"] not in VALID_ROLES:
            errors.append(f"{eid}: role={e['role']!r} 不在 {sorted(VALID_ROLES)}")
        if not re.fullmatch(r"AIU-\d{4}", str(eid)):
            errors.append(f"{eid}: id 须形如 AIU-0001")
        if not str(e.get("date", "")).startswith("20"):
            errors.append(f"{eid}: date={e.get('date')!r} 不是 YYYY-MM-DD")
    return errors


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="AI-use 日志门禁（D7 门禁 6）")
    parser.add_argument("--base", help="对比基线（默认自动探测）")
    parser.add_argument("--files", nargs="*", help="显式指定变更文件（本地试验用）")
    args = parser.parse_args(argv[1:])

    errors = check_structure()
    if errors:
        print(f"FAIL — {LOG_REL} 结构校验未通过，共 {len(errors)} 项：")
        for e in errors:
            print(f"  - {e}")
        return 1
    data = yaml.safe_load(LOG_PATH.read_text(encoding="utf-8"))
    print(f"结构检查通过：{len(data['entries'])} 条 entry")

    base = None if args.files else resolve_base(args.base)
    changed = changed_files(base, args.files)
    trigger = [f for f in changed if CODE_OR_PROMPT_RE.match(f)]

    if not trigger:
        print("PASS — 变更集不含代码或 prompt，无需更新 AI-use 日志")
        return 0

    print(f"变更集含 {len(trigger)} 个代码/prompt 文件（触发门禁 6）：")
    for f in trigger[:10]:
        print(f"  {f}")
    if len(trigger) > 10:
        print(f"  …… 另有 {len(trigger) - 10} 个")

    if LOG_REL in changed:
        print(f"PASS — 同一变更集内已更新 {LOG_REL}")
        return 0

    print()
    print(f"FAIL — 变更集改动了代码或 prompt，但未更新 {LOG_REL}。")
    print("  依据：课程 §6 门禁 6 —— a pull request that changes code or prompts")
    print("        without updating the AI-use log is blocked。")
    print("  处置：在 docs/ai-use-log.yaml 追加一条 entry，记录本次变更的")
    print("        agent / tool / role / task / artifacts / outcome / 人工批准。")
    print("  若本次变更不含 AI 参与（纯人工），仍须追加 entry 并说明 agent 为 human。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
