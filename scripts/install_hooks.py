#!/usr/bin/env python3
"""安装本地 git hooks —— 关闭 `TD-026` 的绕过路径。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\install_hooks.py            # 安装
    .venv\\Scripts\\python.exe scripts\\install_hooks.py --check     # 只检查是否已安装
    .venv\\Scripts\\python.exe scripts\\install_hooks.py --uninstall # 卸载

**为什么需要本脚本**：`TD-026` —— 本项目的 safety-critical 拦截
（`scripts/check_safety_paths.py`）原先**只在 CI 阶段**运行。这使
"改动须附带 ADR"这一约束**滞后**而非前置：本地改完提交，直到 CI 才发现。
课程行 599 要求 **Hook 在事件发生时强制**，而 `.git/hooks/` **不在版本控制内**，
所以 hook 必须由**可复现的脚本**安装 —— 否则"装了 hook"这件事无法被交接与验证。

**安装什么**：
  · `pre-commit`：调用 `check_safety_paths.py`（safety-critical 须 ADR）
    与 `check_ai_use_log.py`（门禁 6）。
  · 两者都**只检查本次暂存的变更**，不改任何文件；发现问题即以非零码退出，
    从而阻止提交。

**不安装什么**（刻意的）：
  · **不装 `pre-push`** —— 推送前的完整门禁太重（全量测试 + 变异验证约数十秒），
    会让人用 `--no-verify` 绕过，反而削弱纪律。重活留给 CI。
  · **不装自动修格式化**（如 `ruff --fix`）—— hook 应只**报告**，
    不应在提交时静默改文件（那会让"我提交了什么"变得不可预测）。
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / ".git" / "hooks"
HOOK_NAME = "pre-commit"
MARKER = "# installed by scripts/install_hooks.py"

# hook 内容：POSIX sh（git for Windows 自带 sh 可执行）
HOOK_BODY = f"""#!/bin/sh
{MARKER}
# 本地 hook —— 关闭 TD-026 的绕过路径。
# 只检查本次提交涉及的变更；发现问题即阻止提交（exit 1）。
# 卸载：python scripts/install_hooks.py --uninstall

set -e

# 已暂存的文件列表（相对仓库根）
STAGED=$(git diff --cached --name-only --diff-filter=ACMR)
if [ -z "$STAGED" ]; then
    exit 0
fi

PY=""
for cand in ".venv/Scripts/python.exe" ".venv/bin/python" "python3" "python"; do
    if command -v "$cand" >/dev/null 2>&1 || [ -x "$cand" ]; then
        PY="$cand"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[pre-commit] 找不到 Python 解释器，跳过本地门禁（CI 仍会检查）" >&2
    exit 0
fi

FAILED=0

echo "[pre-commit] 门禁 2 · safety-critical 路径须附带 ADR ..."
if ! "$PY" scripts/check_safety_paths.py --paths $STAGED; then
    FAILED=1
fi

echo "[pre-commit] 门禁 6 · 改代码或 prompt 须更新 AI-use 日志 ..."
if ! "$PY" scripts/check_ai_use_log.py --files $STAGED; then
    FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
    echo "" >&2
    echo "[pre-commit] 提交被阻止。修复后重试；确需绕过请说明理由并使用 --no-verify。" >&2
    exit 1
fi

echo "[pre-commit] 通过。"
"""


def hooks_dir() -> Path:
    """定位 `.git/hooks`。兼容 `.git` 为文件（worktree/submodule）的情形。"""
    dotgit = ROOT / ".git"
    if dotgit.is_dir():
        return dotgit / "hooks"
    if dotgit.is_file():
        # `gitdir: <path>` —— worktree 或 submodule
        text = dotgit.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            real = Path(text.split(":", 1)[1].strip())
            if not real.is_absolute():
                real = (ROOT / real).resolve()
            return real / "hooks"
    raise SystemExit(f"找不到 git 目录（{dotgit}）—— 本仓库是否已 git init？")


def install() -> int:
    d = hooks_dir()
    d.mkdir(parents=True, exist_ok=True)
    target = d / HOOK_NAME

    if target.exists():
        existing = target.read_text(encoding="utf-8", errors="replace")
        if MARKER not in existing:
            print(f"FAIL — {target} 已存在且**不是**本脚本安装的。", file=sys.stderr)
            print("  为避免覆盖你自己的 hook，本脚本不会改动它。", file=sys.stderr)
            print("  处置：手工合并，或先备份再删除该文件后重试。", file=sys.stderr)
            return 1
        print(f"已存在本脚本安装的 hook，将覆盖：{target}")

    try:
        target.write_text(HOOK_BODY, encoding="utf-8", newline="\n")
        # 加可执行位（Windows 上无实际作用，但跨平台一致）
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError as e:
        print(f"FAIL — 无法写入 {target}：{e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  常见原因：", file=sys.stderr)
        print("   · 受限沙箱不允许写 .git/（agent 会话中常见）", file=sys.stderr)
        print("   · 文件被占用，或当前用户无权限", file=sys.stderr)
        print("", file=sys.stderr)
        print("  处置：在有写权限的环境中重新运行本脚本：", file=sys.stderr)
        print("    python scripts/install_hooks.py", file=sys.stderr)
        print("  CI 门禁不受影响 —— 本 hook 只是把拦截**提前到提交时**（TD-026）。",
              file=sys.stderr)
        return 1

    print(f"OK — 已安装 {target.relative_to(ROOT).as_posix()}")
    print("  检查内容：门禁 2（safety-critical 须 ADR）+ 门禁 6（AI-use 日志）")
    print("  卸载：python scripts/install_hooks.py --uninstall")
    return 0


def check() -> int:
    target = hooks_dir() / HOOK_NAME
    if not target.exists():
        print(f"未安装：{target}")
        print("  这意味着 safety-critical 变更**只在 CI 才被发现**（TD-026）。")
        return 1
    content = target.read_text(encoding="utf-8", errors="replace")
    if MARKER not in content:
        print(f"存在但非本脚本安装：{target}（无法确认其行为）")
        return 1
    if not os.access(target, os.X_OK):
        print(f"已安装但**缺少可执行位**：{target} —— git 可能不会执行它")
        return 1
    print(f"OK — 已安装且可执行：{target.relative_to(ROOT).as_posix()}")
    return 0


def uninstall() -> int:
    target = hooks_dir() / HOOK_NAME
    if not target.exists():
        print(f"无需卸载：{target} 不存在")
        return 0
    content = target.read_text(encoding="utf-8", errors="replace")
    if MARKER not in content:
        print(f"FAIL — {target} 不是本脚本安装的，拒绝删除。", file=sys.stderr)
        return 1
    target.unlink()
    print(f"OK — 已卸载 {target.relative_to(ROOT).as_posix()}")
    print("  注意：CI 门禁不受影响，仍然生效。")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="安装本地 git hooks（关闭 TD-026）")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="只检查是否已安装")
    group.add_argument("--uninstall", action="store_true", help="卸载本脚本安装的 hook")
    args = parser.parse_args(argv)

    if args.check:
        return check()
    if args.uninstall:
        return uninstall()
    return install()


if __name__ == "__main__":
    raise SystemExit(main())
