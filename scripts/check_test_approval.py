#!/usr/bin/env python3
"""测试批准门禁（D7 门禁 1）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\check_test_approval.py
    .venv\\Scripts\\python.exe scripts\\check_test_approval.py --base origin/main
    .venv\\Scripts\\python.exe scripts\\check_test_approval.py --files test/offline/foo.py

课程 §6 门禁 1：
    "Test approval gate — no code change merges unless the tests for the change
     were approved before implementation began."

判定逻辑（两层）：
  ① **结构层**：`docs/test-approvals.yaml` 存在、可解析；每条记录含必需字段；
     `req_ids` 必须真实存在于 `docs/req/requirements.yaml`；`test_files` 必须真实存在；
     `approved_by` 不得为占位符；`approved_at` 须为 ISO 8601 含时区。
  ② **时序层**：变更集中**新增或修改的测试文件**，必须能匹配到一条 `status: approved`
     的记录，且该记录的 `approved_at` **早于**变更集中实现代码的最早提交时间。
     这一层直接实现课程原文的 "approved **before** implementation began"。

⚠️ 生效起点：`docs/test-approvals.yaml` 的 `scope.effective_from`。
   早于该日期引入的测试不受约束（历史缺口不可追溯修复，见 ai-use-log）。

退出码：0 = 通过；1 = 阻断。本脚本只读。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
APPROVALS = ROOT / "docs" / "test-approvals.yaml"
REGISTRY = ROOT / "docs" / "req" / "requirements.yaml"

TEST_FILE_RE = re.compile(r"^test/.*test_.*\.py$")
PLACEHOLDER_RE = re.compile(r"待填|TODO|TBD|xxx", re.IGNORECASE)
REQUIRED = ("id", "req_ids", "test_files", "approved_by", "approved_at", "status")
VALID_STATUS = {"approved", "superseded", "revoked"}


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


def registry_req_ids() -> set[str]:
    if not REGISTRY.exists():
        return set()
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    ids = {r["id"] for r in (data.get("baseline_requirements") or [])}
    ids |= {r["id"] for r in (data.get("candidate_requirements") or [])}
    return ids


def parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def check_structure(valid_reqs: set[str]) -> tuple[list[str], list[dict], str | None]:
    errors: list[str] = []
    if not APPROVALS.exists():
        return [f"测试批准记录不存在: {APPROVALS.relative_to(ROOT).as_posix()}"], [], None

    data = yaml.safe_load(APPROVALS.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return [f"{APPROVALS.name} 顶层必须是对象"], [], None

    effective_from = ((data.get("scope") or {}).get("effective_from")) or None
    approvals = data.get("approvals") or []
    seen: set[str] = set()

    for i, a in enumerate(approvals):
        if not isinstance(a, dict):
            errors.append(f"approvals[{i}] 不是对象")
            continue
        aid = str(a.get("id", f"approvals[{i}]"))
        for f in REQUIRED:
            if f not in a or a[f] in (None, "", []):
                errors.append(f"{aid}: 缺必需字段 {f!r}")
        if aid in seen:
            errors.append(f"{aid}: id 重复")
        seen.add(aid)
        if not re.fullmatch(r"TA-\d{4}", aid):
            errors.append(f"{aid}: id 须形如 TA-0001")
        if a.get("status") and a["status"] not in VALID_STATUS:
            errors.append(f"{aid}: status={a['status']!r} 不在 {sorted(VALID_STATUS)}")
        for rid in a.get("req_ids") or []:
            if rid not in valid_reqs:
                errors.append(f"{aid}: req_ids 含未登记需求 {rid!r}")
        for tf in a.get("test_files") or []:
            if (ROOT / tf).exists():
                continue
            # 预登记：测试**按设计**已批准但尚未创建 —— 这正是门禁 1 想要的状态
            # （"测试先于实现获批"蕴含测试设计先获批）。须显式标注来源计划。
            if a.get("pre_registered"):
                if not a.get("plan"):
                    errors.append(
                        f"{aid}: pre_registered=true 但未声明 plan（预登记的批准必须指向其来源执行计划）"
                    )
                elif not (ROOT / str(a["plan"])).exists():
                    errors.append(f"{aid}: plan 指向不存在的文件 {a['plan']!r}")
            else:
                errors.append(
                    f"{aid}: test_files 指向不存在的文件 {tf!r}"
                    "（若为按设计预登记的测试，请设 pre_registered: true 并声明 plan）"
                )
        # 注意：approved_by 占位符**不在此处判为结构错误**——否则任何 PR（即使只改文档）
        # 都会被全局阻断。占位符记录在下方被排除出"有效批准集合"，
        # 只在其恰被门禁依赖时以具体理由阻断。
        if not parse_iso(str(a.get("approved_at", ""))):
            errors.append(f"{aid}: approved_at 须为 ISO 8601 且含时区")
    return errors, approvals, effective_from


def is_effective(a: dict) -> bool:
    """是否为**可信**的批准记录：状态为 approved 且批准者不是占位符。"""
    return a.get("status") == "approved" and not PLACEHOLDER_RE.search(str(a.get("approved_by", "")))


def implementation_time(changed: list[str], test_files: list[str]) -> datetime | None:
    """变更集中非测试代码的最早提交时间 —— 即"实现开始"的时间下界。"""
    impl = [f for f in changed if f not in test_files]
    if not impl:
        return None
    times: list[datetime] = []
    for f in impl:
        out = git("log", "-1", "--format=%aI", "--", f).strip()
        dt = parse_iso(out)
        if dt:
            times.append(dt)
    return min(times) if times else None


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="测试批准门禁（D7 门禁 1）")
    parser.add_argument("--base", help="对比基线（默认自动探测）")
    parser.add_argument("--files", nargs="*", help="显式指定变更文件（本地试验用）")
    args = parser.parse_args(argv[1:])

    valid_reqs = registry_req_ids()
    errors, approvals, effective_from = check_structure(valid_reqs)
    if errors:
        print(f"FAIL — {APPROVALS.name} 结构校验未通过，共 {len(errors)} 项：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"结构检查通过：{len(approvals)} 条批准记录，生效起点 "
          f"{effective_from or '（未声明）'}")
    placeholders = [a.get("id") for a in approvals if not is_effective(a)]
    if placeholders:
        print(f"  提示：{len(placeholders)} 条记录尚不可信（占位符批准者或非 approved 状态）: "
              f"{placeholders}")

    base = None if args.files else resolve_base(args.base)
    changed = changed_files(base, args.files)
    new_tests = [f for f in changed if TEST_FILE_RE.match(f)]

    if not new_tests:
        print("PASS — 变更集不含测试文件，无需测试批准")
        return 0

    print(f"变更集含 {len(new_tests)} 个测试文件（触发门禁 1）：")
    for f in new_tests:
        print(f"  {f}")

    effective = [a for a in approvals if is_effective(a)]
    impl_dt = implementation_time(changed, new_tests)
    print(f"变更集中实现代码最早提交时间: {impl_dt.isoformat() if impl_dt else '（变更集不含实现代码）'}")

    unapproved: list[str] = []
    for f in new_tests:
        matched = [a for a in effective if f in (a.get("test_files") or [])]
        if not matched:
            invalid = [a.get("id") for a in approvals if f in (a.get("test_files") or [])]
            if invalid:
                unapproved.append(f"{f}（虽有记录 {invalid}，但批准者仍为占位符 → 不可信）")
            else:
                unapproved.append(f"{f}（无任何批准记录）")
            continue
        # 时序：批准必须早于实现开始
        if impl_dt is not None:
            times = [parse_iso(str(a.get("approved_at", ""))) for a in matched]
            times = [t for t in times if t is not None]
            if not times or min(times) >= impl_dt:
                unapproved.append(f"{f}（批准时间不早于实现开始）")

    if unapproved:
        print()
        print(f"FAIL — 以下测试未在实现开始前获批，共 {len(unapproved)} 项：")
        for f in unapproved:
            print(f"  - {f}")
        print()
        print("  依据：课程 §6 门禁 1 —— tests must be approved BEFORE implementation began。")
        print(f"  处置：在 {APPROVALS.relative_to(ROOT).as_posix()} 追加一条 status: approved 的记录，")
        print("        填写 req_ids / test_files / 具名 approved_by / approved_at（ISO 8601 含时区），")
        print("        并确保 approved_at 早于对应实现的提交时间。")
        return 1

    print()
    print("PASS — 变更集中的测试均在实现开始前获得批准")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
