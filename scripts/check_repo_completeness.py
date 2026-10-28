#!/usr/bin/env python3
"""仓库完整性检查（Repository Completeness）——防止"磁盘上有、仓库里没有"。

用法（仓库根目录）：
    python scripts/check_repo_completeness.py
    python scripts/check_repo_completeness.py --verbose

## 为什么需要这个检查（BUG-008 的直接产物）

2026-10-28 队友报告"audit 没有推送"。排查结果是：`.gitignore` 里有一条
**不带前导斜杠**的 `audit/`，而 gitignore 的规则是"匹配任意层级"，
于是它把 `src/audit/`（7 个架构元素之一，证据子系统）整整 3 个文件忽略了 ——
那 3 个文件**从未进入仓库**。

后果是**灾难性的**：`src/app/pipeline.py` 里 `from audit import ...`，
所以任何人 clone 之后 `import app.pipeline` 直接
`ModuleNotFoundError: No module named 'audit'`，5 个测试模块收集失败，
**整个仓库跑不起来**。

**最刺痛的一点**：当时十项检查**全部通过**。为什么？
因为它们**都只读磁盘**，没有一个去问 git"这些东西你要不要交付"。
`fitness_functions.py` 检查 `src/` 的目录结构，`src/audit/` 就在磁盘上；
`audit_implementation.py` 读源码，也在；测试也全过。
**"能被检查"与"能被交付"是两件事，此前没有任何检查覆盖后者。**

本脚本补上这一层：**凡应当交付的源码，必须被 git 跟踪。**

## 检查项

  R1  `src/` 下每个 `.py` 都必须被 git 跟踪
      （架构元素缺文件 = 元素缺失，S1 的盲区）
  R2  `architecture-blueprint.md` §4 声明的每个 `src/<元素>/` 必须存在且已被跟踪
      （防止整个目录被删/被忽略而磁盘遍历发现不了）
  R3  `eval/`、`scripts/`、`docs/`、`data/`、`.github/` 下的交付物必须被跟踪
      （排除显式声明的本地产物）
  R4  关键根目录交付物必须被跟踪（AGENTS.md / Prompt.md / blueprint / config / pyproject …）
  R5  任何**被 gitignore 但看起来像源码**的文件 → FAIL（本次 BUG-008 的形态）
  R6  已跟踪的 `src/` 文件不得在磁盘上缺失（反向一致性）

退出码：0 = 通过；1 = 存在未交付的源码。本脚本只读。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 要交付的源码根（相对仓库根）
SOURCE_ROOTS = ("src", "eval", "scripts", "docs", "data", ".github", ".agent", ".opencode")
# 视为源码/交付物的扩展名
SOURCE_SUFFIXES = {
    ".py", ".md", ".yaml", ".yml", ".json", ".jsonc", ".toml", ".cfg", ".ini", ".txt",
}

# **显式声明**的本地产物：允许存在但不必交付。
# 加东西到这里要谨慎 —— 每一条都是"我确认它不该进仓库"。
LOCAL_ARTIFACT_GLOBS = (
    "scripts/_*.py",              # BUG-008 同期清理的一次性探针（待人工删除）
    "eval/reports/replay-*.json",  # 评估集 replay 报告（运行期产物）
)

# 构建/缓存目录：不是交付物，磁盘遍历时直接跳过。
# （它们已被 .gitignore 覆盖，但本脚本的磁盘遍历不读 gitignore，故需独立排除。）
BUILD_DIR_MARKERS = (
    ".egg-info", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", "/build/", "/dist/",
)

# 关键根目录交付物（R4）
ROOT_DELIVERABLES = (
    "README.md",
    "AGENTS.md",
    "Prompt.md",
    "architecture-blueprint.md",
    "config.yaml",
    "pyproject.toml",
    ".gitignore",
)


def git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout


def tracked_files() -> set[str]:
    """全部被 git 跟踪的文件（posix 相对路径）。"""
    code, out = git("ls-files", "-z")
    if code != 0:
        return set()
    return {p for p in out.split("\0") if p}


def is_local_artifact(rel: str) -> bool:
    """是否属于显式声明的本地产物或构建/缓存目录。"""
    for pattern in LOCAL_ARTIFACT_GLOBS:
        if Path(rel).match(pattern):
            return True
    for marker in BUILD_DIR_MARKERS:
        if marker in rel:
            return True
    return False


def on_disk_sources() -> dict[str, list[str]]:
    """{根: [相对路径…]} —— 磁盘上应交付的源码文件。"""
    found: dict[str, list[str]] = {}
    for root_name in SOURCE_ROOTS:
        root = ROOT / root_name
        if not root.is_dir():
            continue
        items: list[str] = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in SOURCE_SUFFIXES:
                continue
            rel = p.relative_to(ROOT).as_posix()
            if is_local_artifact(rel):
                continue
            items.append(rel)
        found[root_name] = sorted(items)
    return found


def declared_elements() -> list[str]:
    """从 `architecture-blueprint.md` §4 解析 `src/<元素>/` 清单（唯一来源）。"""
    bp = ROOT / "architecture-blueprint.md"
    if not bp.exists():
        return []
    text = bp.read_text(encoding="utf-8")
    # 只取 §4 Components 一节，避免匹配正文其它地方的 src/ 路径
    m = re.search(r"^## 4\.\s*Components.*?(?=^## )", text, re.M | re.S)
    section = m.group(0) if m else text
    names: list[str] = []
    for hit in re.findall(r"`src/([A-Za-z0-9_]+)/`", section):
        if hit not in names:
            names.append(hit)
    return names


def ignored_but_looks_like_source() -> list[str]:
    """R5：被 gitignore 但看起来像源码的文件（BUG-008 的形态）。"""
    code, out = git("status", "--ignored", "--porcelain")
    if code != 0:
        return []
    bad: list[str] = []
    for line in out.splitlines():
        if not line.startswith("!! "):
            continue
        rel = line[3:].strip().strip('"').replace("\\", "/")
        if rel.endswith("/"):          # 整个目录被忽略
            rel = rel.rstrip("/")
        if is_local_artifact(rel + "/x.py") or is_local_artifact(rel):
            continue
        if Path(rel).suffix in SOURCE_SUFFIXES:
            bad.append(rel)
    return sorted(bad)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="仓库完整性检查（未交付源码检测）")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    tracked = tracked_files()
    if not tracked:
        print("⚠️ 无法获取 git 跟踪列表（是否在 git 仓库内？）—— 跳过检查")
        return 0

    failures: list[str] = []
    notes: list[str] = []

    # ---- R1/R3：磁盘上应交付的源码必须被跟踪 ----
    sources = on_disk_sources()
    total = 0
    for root_name, files in sources.items():
        untracked = [f for f in files if f not in tracked]
        total += len(files)
        for f in untracked:
            failures.append(f"[R1/R3] 源码文件存在但**未被 git 跟踪**（不会交付）: {f}")

    # ---- R2：blueprint 声明的架构元素必须存在且已交付 ----
    elements = declared_elements()
    if not elements:
        failures.append("[R2] 无法从 architecture-blueprint.md §4 解析架构元素清单")
    for name in elements:
        rel_dir = f"src/{name}"
        if not (ROOT / rel_dir).is_dir():
            failures.append(f"[R2] 架构元素目录缺失: {rel_dir}/（blueprint §4 已声明）")
            continue
        delivered = [p for p in tracked if p.startswith(rel_dir + "/")]
        if not delivered:
            failures.append(
                f"[R2] 架构元素 {rel_dir}/ **在仓库中没有任何文件** —— "
                "磁盘上存在但未交付（BUG-008 的形态）"
            )

    # ---- R4：根目录关键交付物 ----
    for name in ROOT_DELIVERABLES:
        if not (ROOT / name).exists():
            failures.append(f"[R4] 关键交付物磁盘上不存在: {name}")
        elif name not in tracked:
            failures.append(f"[R4] 关键交付物未被 git 跟踪: {name}")

    # ---- R5：被忽略但像源码 ----
    for rel in ignored_but_looks_like_source():
        failures.append(
            f"[R5] 被 .gitignore 忽略，但它看起来是源码/交付物: {rel} —— "
            "检查 gitignore 模式是否缺少前导 `/`（BUG-008 的根因）"
        )

    # ---- R6：已跟踪文件不得在磁盘缺失 ----
    for rel in sorted(tracked):
        if rel.endswith("/"):
            continue
        if not (ROOT / rel).exists():
            failures.append(f"[R6] 已被 git 跟踪但磁盘上缺失: {rel}")

    # ---- 输出 ----
    print("=" * 74)
    print("仓库完整性检查（磁盘上有 ≠ 仓库里有）")
    print("=" * 74)
    print(f"git 跟踪文件总数: {len(tracked)}")
    print(f"磁盘待交付源码 : {total}（{len(sources)} 个根）")
    print(f"blueprint §4 架构元素: {len(elements)} → {', '.join(elements) or '(未解析到)'}")
    if args.verbose:
        for root_name, files in sources.items():
            print(f"  {root_name}/: {len(files)} 个文件")

    if failures:
        print()
        print(f"FAIL — {len(failures)} 项：")
        for f in failures:
            print(f"  - {f}")
        print()
        print("依据：BUG-008 —— 十项检查全绿，但 src/audit/ 因 gitignore 的 `audit/`")
        print("      模式（缺前导 `/`，匹配任意层级）从未交付，导致 clone 后 import 失败。")
        return 1

    for n in notes:
        print(f"  {n}")
    print()
    print("PASS — 磁盘上的全部交付物都已进入仓库；架构元素无缺失。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
