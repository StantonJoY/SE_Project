#!/usr/bin/env python3
"""安全关键路径变更检查（D7 门禁 2 的"safety-relevant paths"部分）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\check_safety_paths.py
    .venv\\Scripts\\python.exe scripts\\check_safety_paths.py --base origin/main
    .venv\\Scripts\\python.exe scripts\\check_safety_paths.py --paths src/compliance/pipeline.py
    .venv\\Scripts\\python.exe scripts\\check_safety_paths.py --show-paths

背景（课程 §6 门禁 2）：
    "contract, security, API-surface, and permission checks run on any pull request
     touching safety-relevant paths."
背景（课程 §6 分支保护）：
    "changes to safety-critical paths must require human review with an accompanying
     architecture decision."

本脚本实现"accompanying architecture decision"这一半的**机器可判定部分**：
若某个 PR 触及安全关键路径，则必须同时满足
  ① 变更集里**新增或修改了 ADR 文件**，或
  ② 提交信息/PR 标题中**引用了 ADR ID**（如 `ADR-001`）。
否则以非零退出码阻断（fail-closed）。

安全关键路径清单**从 ADR 的表格解析**，不在此处硬编码——
避免清单与架构决策记录漂移（这是本项目在 `BUG-007` 中学到的教训）。

**多份 ADR 的合并规则（ADR-004 引入）**：
  清单原本只在 `ADR-002` §2 D4。当需要**新增受保护路径**时，按 ADR 的**冻结语义**
  不应直接改写已 `Accepted` 的 ADR，而应新建一份 ADR 并**显式声明**它承载补充清单。
  故本脚本支持多份 ADR，识别方式是一个**显式标记**（而不是"扫描所有表格"）：

      <!-- safety-critical-paths -->

  标记之后**紧邻的那张表**被视为受保护路径清单。用显式标记而非全表扫描的理由：
  其它 ADR 表格（如"备选方案对比""重开触发器"）也可能出现路径字符串，
  无差别解析会把它们误当成受保护路径。

退出码：0 = 通过或无需检查；1 = 存在阻断项。本脚本只读。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / "docs" / "architecture"

# 承载受保护路径清单的表必须带此标记（HTML 注释，渲染时不可见）
PATH_TABLE_MARKER = "<!-- safety-critical-paths -->"

# 匹配**真正的标记行**：整行（去空白后）恰为该注释。
# ⚠️ 不能用朴素的 `marker in line` —— 标记字符串会在文档的**散文里被引用**
#    （例如本 ADR-004 的"说明"段就写了它），那时会匹配到错误的行，
#    解析出错误的表格（实测踩过：ADR-004 的说明段被当成标记，导致清单全部
#    被判为"仅只读"）。这正是"显式声明"必须严格匹配的理由。
PATH_TABLE_MARKER_RE = re.compile(r"^\s*" + re.escape(PATH_TABLE_MARKER) + r"\s*$")

# 从 ADR-002 §2 D4 的表格行解析受保护路径，例如：
#   | `src/compliance/` | Read | **No access** | **是 — 须 ADR** |
#   | `data/banned_words.json`、`data/scene_rules.json` | Read | **No access** | **是 — 须 ADR** |
#   | `test/offline/`   | Read | Read/Write     | 否 |
# 注意：一行可含多个被反引号包裹的路径（用、分隔），必须全部收录。
PATH_RE = re.compile(r"`([^`]+)`")
HEADER_CELLS = {"Path / resource", "Path", "路径"}


def _parse_path_table(lines: list[str], start: int) -> dict[str, bool]:
    """从 `lines[start:]` 起解析第一张表格，返回 {路径: 是否强制 ADR}。"""
    paths: dict[str, bool] = {}
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if paths:
                break  # 表格结束
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0] in HEADER_CELLS:
            continue
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue  # 表头分隔行
        last = cells[-1]
        for path in PATH_RE.findall(cells[0]):
            if "/" not in path and not path.endswith((".json", ".py", ".md")):
                continue  # 非路径条目（如机制名）
            paths[path] = "ADR" in last
    return paths


def read_adr_paths() -> tuple[dict[str, bool], list[str]]:
    """合并全部 ADR 中**带标记**的受保护路径清单。

    返回 `(路径 → 是否强制 ADR, 贡献了清单的 ADR 文件名列表)`。

    识别方式：ADR 中某个 `<!-- safety-critical-paths -->` 标记之后的**第一张表格**。
    这样新增受保护路径只需新建一份 ADR 并放上标记 —— 无需改写已冻结的 ADR-002。
    """
    paths: dict[str, bool] = {}
    contributors: list[str] = []
    if not ADR_DIR.is_dir():
        return {}, []
    for adr in sorted(ADR_DIR.glob("adr-*.md")):
        lines = adr.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not PATH_TABLE_MARKER_RE.match(line):
                continue
            found = _parse_path_table(lines, i + 1)
            if found:
                paths.update(found)
                contributors.append(adr.name)
            break  # 每份 ADR 只取第一个标记
    return paths, contributors


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


def changed_files(base: str | None) -> list[str]:
    if base:
        out = git("diff", "--name-only", f"{base}...HEAD")
    else:
        out = ""
    if not out.strip():
        # 退化：未提交变更 + 最近一次提交
        out = git("status", "--porcelain")
        files = [line[3:].strip() for line in out.splitlines() if line.strip()]
        out = git("diff", "--name-only", "HEAD~1", "HEAD")
        files += out.splitlines()
        return sorted({f for f in files if f})
    return sorted({f for f in out.splitlines() if f.strip()})


def touches(path: str, changed: list[str]) -> list[str]:
    """判断某受保护路径是否被触及（目录前缀或精确文件）。"""
    hits = []
    for f in changed:
        if path.endswith("/"):
            if f.startswith(path):
                hits.append(f)
        elif f == path:
            hits.append(f)
    return hits


def adr_referenced(changed: list[str]) -> tuple[bool, str]:
    """变更集是否含 ADR 文件变更，或提交信息引用了 ADR ID。"""
    adr_changed = [f for f in changed if "architecture/adr" in f or re.search(r"adr-\d+", f)]
    if adr_changed:
        return True, f"变更集含 ADR 文件: {adr_changed}"
    log = git("log", "-5", "--pretty=%s%n%b")
    ids = sorted(set(re.findall(r"ADR-\d+", log)))
    if ids:
        return True, f"提交信息引用 {ids}"
    return False, "变更集与提交信息中均无 ADR 引用"


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="安全关键路径变更检查（D7 门禁 2）")
    parser.add_argument("--base", help="对比基线（默认自动探测 origin/main → main → HEAD~1）")
    parser.add_argument("--paths", nargs="*", help="显式指定变更文件（用于本地试验，跳过 git）")
    parser.add_argument("--show-paths", action="store_true", help="只打印解析到的安全路径清单")
    args = parser.parse_args(argv[1:])

    paths, contributors = read_adr_paths()
    if not paths:
        print(
            "FAIL — 无法从任何 ADR 解析安全关键路径清单"
            f"（须有 `{PATH_TABLE_MARKER}` 标记的表格；清单缺失即无法判定，fail-closed）"
        )
        return 1

    if args.show_paths:
        print(f"从 {len(contributors)} 份 ADR 合并解析到 {len(paths)} 条受保护路径：")
        print(f"  清单来源: {', '.join(contributors)}")
        for p, need_adr in sorted(paths.items()):
            print(f"  {'[须 ADR]' if need_adr else '[仅只读]'} {p}")
        return 0

    if args.paths:
        changed = sorted(set(args.paths))
        base_label = "（显式指定）"
    else:
        base = resolve_base(args.base)
        changed = changed_files(base)
        base_label = base or "（工作区未提交变更）"

    print(f"对比基线: {base_label}")
    print(f"变更文件 {len(changed)} 个")

    touched: dict[str, list[str]] = {}
    for p in paths:
        hits = touches(p, changed)
        if hits:
            touched[p] = hits

    if not touched:
        print("PASS — 未触及任何受保护路径，无需架构决策")
        return 0

    print()
    print("触及的受保护路径：")
    for p, hits in sorted(touched.items()):
        print(f"  {'[须 ADR]' if paths[p] else '[仅只读]'} {p} ← {hits}")

    # 只有"须 ADR"的路径才要求伴随架构决策；"仅只读"路径的记录供人工评审参考
    need_adr = {p: h for p, h in touched.items() if paths[p]}
    if not need_adr:
        print()
        print("PASS — 触及的均为只读路径（不强制 ADR），但变更仍须人工评审")
        return 0

    ok, why = adr_referenced(changed)
    print()
    print(f"架构决策伴随检查: {'通过' if ok else '未通过'} — {why}")
    if ok:
        print("PASS — 触及须 ADR 的路径且伴随架构决策")
        return 0

    print()
    print("FAIL — 触及须 ADR 的安全关键路径，但缺少伴随的架构决策。")
    print(f"  涉及路径: {sorted(need_adr)}")
    print("  依据：课程 §6 分支保护 —— safety-critical paths 的变更须人工评审并附带架构决策。")
    print("  处置：在本 PR 中新增/修改 docs/architecture/adr-NNN-*.md，或在提交信息中引用 ADR ID。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
