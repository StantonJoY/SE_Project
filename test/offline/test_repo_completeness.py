"""仓库交付完整性 的离线测试。

Verifies: REQ-ADS-GOV-001（审计证据子系统必须真实存在于交付物中）、
          INV-ADS-012（每次请求恰好 1 条审计 —— 缺 `src/audit/` 则该不变量根本无法强制）、
          REQ-ADS-NFR-QA-002（验证完整性：交付物缺失必须在 CI 可见）。
          以及 `scripts/check_repo_completeness.py` 的判定与 BUG-008 的根因不再复发。
批准：本文件随 BUG-008 修复一并提交（缺陷修复的回归测试；设计依据见 BUG-008）。
运行：仓库根目录下 pytest test/offline/test_repo_completeness.py

## 为什么这个测试必须存在（BUG-008）

队友报告「audit 没有推送」。根因是 `.gitignore` 里一条**不带前导斜杠**的 `audit/`
（本意只忽略仓库根的运行期日志目录），而 gitignore 的规则是「无前导斜杠的模式
匹配任意层级」——于是 `src/audit/`（证据子系统，7 个元素之一）整目录被忽略，
3 个文件**从未进入仓库**，任何人 clone 后 `import app.pipeline` 直接
`ModuleNotFoundError: No module named 'audit'`。

**最刺痛的是：当时十项检查全部通过**，因为它们**都只读磁盘**，没有一个去问
git「这些要不要交付」。所以本文件的核心不是"再测一遍代码"，而是
**把"源码必须被 git 跟踪"这条性质变成可失败的断言**。

在非 git 环境（例如 `git archive` 导出的干净副本）下，本文件的用例会
`pytest.skip`——因为那些性质只能对 git 工作树断言。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout


def in_git_repo() -> bool:
    return git("rev-parse", "--is-inside-work-tree")[0] == 0


needs_git = pytest.mark.skipif(not in_git_repo(), reason="需要 git 工作树（导出副本无 .git）")


def src_packages() -> list[Path]:
    src = ROOT / "src"
    if not src.is_dir():
        return []
    return sorted(p for p in src.iterdir() if p.is_dir() and (p / "__init__.py").exists())


# ---- BUG-008 的**直接**回归断言 ----

@needs_git
@pytest.mark.parametrize("pkg", [p.name for p in src_packages()])
def test_no_src_package_is_gitignored(pkg: str) -> None:
    """BUG-008（反例）：**任何 `src/` 包都不得被 gitignore 命中**。

    这条是本缺陷最精确的回归保护：它不测业务逻辑，只测
    「gitignore 有没有再一次吃掉源码目录」。

    典型失败形态：`.gitignore` 里出现不带前导 `/` 的目录名
    （如 `audit/`），gitignore 会把它匹配到**任意层级**，
    于是 `src/audit/` 被静默排除出交付物。

    ⚠️ **必须用 `--no-index`**：`git check-ignore` 默认**跳过已跟踪文件**
    （尊重索引），因此对已入库的 `src/audit/store.py` 会报"未忽略" ——
    那样这条断言就**永远不会失败**，等于没有保护（实测踩过）。
    `--no-index` 只看模式本身，才是真正在测"将来新增的 src 包会不会被吞"。
    """
    files = sorted((ROOT / "src" / pkg).glob("*.py"))
    assert files, f"src/{pkg}/ 下没有 .py —— 包是否已空？"
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        code, out = git("check-ignore", "--no-index", "-v", rel)
        assert code != 0, (
            f"{rel} 被 gitignore 模式命中，将来新增的同类文件将不会交付：\n{out.strip()}\n"
            "检查 .gitignore 的模式是否缺少前导 `/`（BUG-008）"
        )


@needs_git
def test_every_src_file_is_tracked() -> None:
    """BUG-008（反例）：`src/` 下每个 `.py` 都必须已被 git 跟踪。

    「磁盘上有」不等于「仓库里有」——前者十项检查都能看见，后者没人检查。
    """
    code, out = git("ls-files", "-z")
    assert code == 0
    tracked = {p for p in out.split("\0") if p}
    missing = []
    for f in sorted((ROOT / "src").rglob("*.py")):
        rel = f.relative_to(ROOT).as_posix()
        if rel not in tracked:
            missing.append(rel)
    assert not missing, f"以下源码存在但未被 git 跟踪（不会交付）: {missing}"


@needs_git
def test_all_declared_elements_are_delivered() -> None:
    """BUG-008（反例）：blueprint §4 声明的每个架构元素都必须在仓库里有文件。"""
    code, out = git("ls-files", "-z")
    assert code == 0
    tracked = [p for p in out.split("\0") if p]
    for pkg in src_packages():
        prefix = f"src/{pkg.name}/"
        assert any(p.startswith(prefix) for p in tracked), (
            f"架构元素 {prefix} 在仓库中没有任何文件（BUG-008 的形态）"
        )


@needs_git
def test_no_junk_is_tracked() -> None:
    """BUG-008 同期清理：仓库中不得跟踪缓存、探针或构建产物。"""
    code, out = git("ls-files", "-z")
    assert code == 0
    tracked = [p for p in out.split("\0") if p]
    junk_markers = (
        "__pycache__", ".pyc", "pytest_cache", "ruff_cache", "mypy_cache",
        "egg-info", ".probe", ".dsh_", ".tmp", ".bak",
    )
    bad = [p for p in tracked if any(m in p for m in junk_markers)]
    assert not bad, f"仓库中跟踪了不应交付的文件: {bad}"


# ---- 检查器自身的可用性 ----

def test_checker_script_exists() -> None:
    """仓库完整性检查器必须存在（缺失即失去这一层保护）。"""
    assert (ROOT / "scripts" / "check_repo_completeness.py").exists()


def test_checker_parses_seven_elements() -> None:
    """检查器须能从 blueprint §4 解析出 7 个架构元素（判据单一来源）。"""
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_repo_completeness as crc

    elements = crc.declared_elements()
    assert len(elements) == 7, f"应为 7 个元素，实际 {elements}"
    assert set(elements) == {
        "ads", "scene", "compliance", "selector", "render", "audit", "app",
    }


def test_checker_recognises_local_artifacts() -> None:
    """检查器须把显式声明的本地产物排除在外（否则误报）。"""
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_repo_completeness as crc

    assert crc.is_local_artifact("scripts/_probe_sessions.py")
    assert crc.is_local_artifact("eval/reports/replay-20261028T120000.json")
    assert crc.is_local_artifact("src/ad_recommender.egg-info/SOURCES.txt")
    assert not crc.is_local_artifact("src/audit/store.py")


@needs_git
def test_checker_passes_on_current_tree() -> None:
    """检查器在当前工作树上必须 PASS（否则要么真有问题，要么它误报）。"""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_repo_completeness.py")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, f"检查器 FAIL：\n{proc.stdout}\n{proc.stderr}"
