#!/usr/bin/env python3
"""结构性架构 fitness function（课程 Tier 1 验证 / CI 结构门）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\fitness_functions.py

实现 `docs/code-governance/structural-constraints.md` 的可自动化检查项：
  S1  一个元素一个模块：src/ 每个包恰好映射一个架构元素；反之每个元素必须有实现或明确标记未建
  S2  扩展永不删除：V1 为 forward build；检查 authority 边界是否被绕过（无模块私自调用 compliance 之外的裁决路径）
  S3  ADR docstring 可追溯性：每个 src 模块 docstring 至少引用一条 ADR / REQ / INV ID

以及 `verification-constraints.md` 的可自动化检查项：
  V1  每条 fit criterion ≥ 1 个测试
  V2  每条 invariant ≥ 1 个反例（失败）测试
  V3  每个测试模块引用 REQ / INV ID（并把所属模块映射到架构元素）
  V4  跨轮次无回归（本轮以「全部既有测试模块必须存在」为实现，测试执行由 pytest 负责）

**依赖原则**：这些检查完全独立于任何 LLM，机械执行，失败即拒绝构建（课程行 3857）。

退出码：0 = 全部通过；1 = 有 FAIL。
本脚本只读。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "req" / "requirements.yaml"
TRACE_MATRIX = ROOT / "docs" / "architecture" / "trace-matrix.md"
SRC = ROOT / "src"
TEST_DIR = ROOT / "test" / "offline"

REQ_RE = re.compile(r"\bREQ-[A-Z0-9-]+")
INV_RE = re.compile(r"\bINV-[A-Z0-9-]+")
ID_REF_RE = re.compile(r"\b(?:REQ|INV|ADR)-[A-Z0-9-]+")
NEGATIVE_MARKERS = ("反例", "negative test", "must fail", "会失败")
COVERAGE_MAP = ROOT / "docs" / "code-governance" / "acceptance-coverage-map.yaml"

# S1：包名 → 架构元素（来自 architecture-blueprint.md §4 组件分解）
# 注：bidding 为 V2（docs2/ 轮次）预留包，登记在此以免 V2 开工时触发 S1 误报。
ELEMENT_BY_PACKAGE = {
    "ads": "① 素材契约 + 候选集构建",
    "scene": "② 场景输入契约",
    "compliance": "③ FINAL AUTHORITY（确定性合规管道）",
    "selector": "④ AI 建议层（闭集选择 + 上下文装配 + 解释）",
    "render": "⑤ 输出契约",
    "audit": "⑥ 证据子系统",
    "app": "⑦ 编排 / pipeline / CLI / 降级路径",
    "bidding": "⑧ [V2 预留] 竞价引擎",
}

# V4：本轮之前必须存在的测试模块（本轮新增模块不在此列，视为 append）
REQUIRED_TEST_MODULES = {
    "test_ads.py",
    "test_scene.py",
    "test_compliance.py",
    "test_banned_words.py",
    "test_requirements_registry.py",
    # P4（selector）新增；纳入后即受回归门保护，不得删除
    "test_selector.py",
    "test_context_assembly.py",
    "test_explanation.py",
    # P5+P6（app / render / audit）新增
    "test_app_pipeline.py",
    "test_render.py",
    "test_audit.py",
    "test_sanitize.py",
    # P7（评估集 / 版本溯源 / 变异验证）新增
    "test_eval_runner.py",
    "test_mutation_check.py",
    "test_provenance.py",
    # BUG-008（交付完整性）新增：把"源码必须被 git 跟踪"变成会失败的反例
    "test_repo_completeness.py",
}

# S2：authority 边界——这些包不得被"展示路径"直接绕过 compliance 调用
DECISION_PACKAGES = {"selector", "render", "audit"}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def fail(self, check: str, msg: str) -> None:
        self.failures.append(f"[{check}] {msg}")

    def note(self, msg: str) -> None:
        self.notes.append(msg)


def load_registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# S1 一个元素一个模块
# --------------------------------------------------------------------------

def check_s1(rep: Report, registry: dict) -> None:
    declared = {e.split(".")[0] for e in collect_enforcement_targets(registry)}
    actual = {p.name for p in SRC.iterdir() if p.is_dir() and (p / "__init__.py").exists()}

    for pkg in sorted(actual - set(ELEMENT_BY_PACKAGE)):
        rep.fail("S1", f"src/{pkg}/ 未映射到任何架构元素（蓝图 §4 未声明）")
    undeclared = sorted(pkg for pkg in actual if pkg not in declared)
    for pkg in undeclared:
        rep.fail("S1", f"src/{pkg}/ 存在实现但没有任何需求的 enforcement 指向它（孤儿模块）")
    for pkg in sorted(set(ELEMENT_BY_PACKAGE) - actual):
        rep.note(f"S1: 元素 {pkg}（{ELEMENT_BY_PACKAGE[pkg]}）尚无实现——设计已就位，代码待建")
    rep.note(f"S1: 已实现包 {sorted(actual)}，均一对一映射到架构元素")


def collect_enforcement_targets(registry: dict) -> set[str]:
    out: set[str] = set()
    for section in ("baseline_requirements", "candidate_requirements"):
        for r in registry.get(section) or []:
            for e in r.get("enforcement") or []:
                # 形如 "compliance.pipeline.run_compliance" 或 "test.offline" 或 ".opencode/..."
                head = e.split(".")[0].strip()
                if head and not head.startswith(".") and "/" not in head:
                    out.add(e)
    return out


# --------------------------------------------------------------------------
# S2 扩展永不删除 + authority 边界
# --------------------------------------------------------------------------

def check_s2(rep: Report) -> None:
    """V1 是 forward build：src/ 全部为本轮新增，不存在"改动基线"的问题。

    因此 S2 在本轮的**可检查形式**是 authority 边界：
    不得存在绕过 compliance 的展示路径。
    """
    compliance_pkg = SRC / "compliance"
    if not compliance_pkg.exists():
        rep.fail("S2", "src/compliance/ 不存在——权威边界缺失")
        return
    # 决策包不得 import compliance 之外就自行决定展示
    for pkg in sorted(DECISION_PACKAGES):
        pkg_dir = SRC / pkg
        if not pkg_dir.exists():
            continue
        for py in pkg_dir.rglob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            imported = {
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            } | {
                (node.module or "").split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            rep.note(f"S2: {py.relative_to(ROOT).as_posix()} imports {sorted(imported)}")

    # ---- 权威边界的**机械强制**：建议层不得反向依赖裁决层 ----
    # selector 是 advisory，compliance 是 FINAL AUTHORITY。若 selector 能调用
    # compliance，权威边界即倒置（concern-clusters.md §0 明令两簇不得混）。
    # 该禁令在 docs/plans/P4-selector.md ③ 中已声明，此处使其可机械检查。
    forbidden = {"compliance"}
    for py in sorted((SRC / "selector").rglob("*.py")) if (SRC / "selector").exists() else []:
        tree = ast.parse(py.read_text(encoding="utf-8"))
        tops: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                tops |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                tops.add((node.module or "").split(".")[0])
        bad = tops & forbidden
        if bad:
            rep.fail(
                "S2",
                f"{py.relative_to(ROOT).as_posix()} 导入了 {sorted(bad)} —— "
                "建议层（selector）不得反向依赖裁决层（compliance），权威边界会倒置",
            )

    # 反向：compliance 也不得依赖 selector（裁决层不应知道建议层如何实现）
    for py in sorted((SRC / "compliance").rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        tops = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                tops |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                tops.add((node.module or "").split(".")[0])
        if "selector" in tops:
            rep.fail(
                "S2",
                f"{py.relative_to(ROOT).as_posix()} 导入了 selector —— "
                "裁决层不得依赖建议层",
            )

    rep.note("S2: 权威边界已机械检查（selector ↮ compliance 双向禁止依赖）")
    rep.note("S2: V1 forward build——src/ 全为本轮新增，无基线文件被修改（S2 的『永不替换』本轮无适用对象）")


# --------------------------------------------------------------------------
# S3 ADR docstring 可追溯性
# --------------------------------------------------------------------------

def check_s3(rep: Report) -> None:
    for py in sorted(SRC.rglob("*.py")):
        rel = py.relative_to(ROOT).as_posix()
        tree = ast.parse(py.read_text(encoding="utf-8"))
        doc = ast.get_docstring(tree) or ""
        if not doc.strip():
            rep.fail("S3", f"{rel} 缺模块 docstring（须引用架构决策与不变量）")
            continue
        if not ID_REF_RE.search(doc):
            rep.fail("S3", f"{rel} 的 docstring 未引用任何 ADR / REQ / INV ID")


# --------------------------------------------------------------------------
# V1 / V2 / V3 / V4
# --------------------------------------------------------------------------

def read_test_corpus() -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted(TEST_DIR.glob("test_*.py"))
    }


def load_coverage_map() -> dict:
    return yaml.safe_load(COVERAGE_MAP.read_text(encoding="utf-8"))


def check_v1(rep: Report, registry: dict, corpus: dict[str, str]) -> None:
    """V1：每条 fit criterion ≥ 1 测试。

    判定依据 `acceptance-coverage-map.yaml`（诚实映射），**且**该映射自身的自洽性必须成立：
      - 声明 `test_backed: true` 的需求，其 ID 必须真的出现在某个测试模块中；
      - 每条基线需求都必须出现在映射表中；
      - `test_backed: false` 的需求必须给出去向（pending_test）与阻塞原因（blocked_by）。
    """
    joined = "\n".join(corpus.values())
    cov = load_coverage_map()
    entries = {e["id"]: e for e in cov.get("requirements") or []}

    baseline = [r["id"] for r in registry.get("baseline_requirements") or []]
    for rid in baseline:
        if rid not in entries:
            rep.fail("V1", f"{rid} 未出现在 acceptance-coverage-map.yaml 中")

    backed = 0
    for rid, e in entries.items():
        if e.get("test_backed"):
            backed += 1
            if rid not in joined:
                rep.fail(
                    "V1",
                    f"{rid} 在覆盖表中声明 test_backed=true，但没有任何测试模块引用它（映射与事实不符）",
                )
        else:
            if not e.get("pending_test"):
                rep.fail("V1", f"{rid} 未覆盖但未声明 pending_test")
            if not e.get("blocked_by"):
                rep.fail("V1", f"{rid} 未覆盖但未声明 blocked_by")

    rep.note(f"V1: 需求覆盖 {backed}/{len(baseline)} 有测试证据，其余见 acceptance-coverage-map.yaml")


def check_v2(rep: Report, registry: dict, corpus: dict[str, str]) -> None:
    """V2：每条不变量 ≥ 1 个"会失败"的反例测试。

    判定依据 `acceptance-coverage-map.yaml` 的 `negative_test_backed`，
    且声明为 true 的不变量 ID 必须真的出现在**含反例标记**的测试模块中。
    """
    negative_text = "\n".join(
        text for text in corpus.values() if any(m in text for m in NEGATIVE_MARKERS)
    )
    cov = load_coverage_map()
    entries = {e["id"]: e for e in cov.get("invariants") or []}

    # 登记册与 invariants.md 声明的全部不变量
    declared: set[str] = set()
    for r in registry.get("baseline_requirements") or []:
        declared.update(r.get("invariants") or [])
    inv_doc = ROOT / "docs" / "architecture" / "invariants.md"
    if inv_doc.exists():
        declared |= set(
            re.findall(r"`(INV-[A-Z0-9-]*[0-9]+)`", inv_doc.read_text(encoding="utf-8"))
        )

    for inv in sorted(declared):
        if inv not in entries:
            rep.fail("V2", f"{inv} 未出现在 acceptance-coverage-map.yaml 中")
            continue
        e = entries[inv]
        if e.get("negative_test_backed"):
            if inv not in negative_text:
                rep.fail(
                    "V2",
                    f"{inv} 声明 negative_test_backed=true，但没有任何含反例标记的测试引用它",
                )
        else:
            if not e.get("pending_test"):
                rep.fail("V2", f"{inv} 无反例测试但未声明 pending_test")
            if not e.get("blocked_by"):
                rep.fail("V2", f"{inv} 无反例测试但未声明 blocked_by")

    backed = sum(1 for e in entries.values() if e.get("negative_test_backed"))
    rep.note(f"V2: 不变量反例覆盖 {backed}/{len(declared)}，其余见 acceptance-coverage-map.yaml")


def check_v3(rep: Report, corpus: dict[str, str]) -> None:
    for name, text in sorted(corpus.items()):
        doc = ast.get_docstring(ast.parse(text)) or ""
        if not ID_REF_RE.search(doc):
            rep.fail("V3", f"{name} 的模块 docstring 未引用它验证的 REQ / INV ID")


def check_v4(rep: Report, corpus: dict[str, str]) -> None:
    missing = sorted(REQUIRED_TEST_MODULES - set(corpus))
    for name in missing:
        rep.fail("V4", f"既有的测试模块 {name} 消失——回归门失败（不得删除测试）")


# --------------------------------------------------------------------------
# 与 trace matrix 的一致性
# --------------------------------------------------------------------------

def check_trace_sync(rep: Report, registry: dict) -> None:
    if not TRACE_MATRIX.exists():
        rep.fail("TRACE", f"缺 {TRACE_MATRIX.relative_to(ROOT).as_posix()}")
        return
    text = TRACE_MATRIX.read_text(encoding="utf-8")
    for r in registry.get("baseline_requirements") or []:
        if r["id"] not in text:
            rep.fail("TRACE", f"{r['id']} 未出现在 trace-matrix.md 中（每条需求都必须可追溯）")


# --------------------------------------------------------------------------

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    registry = load_registry()
    corpus = read_test_corpus()
    rep = Report()

    check_s1(rep, registry)
    check_s2(rep)
    check_s3(rep)
    check_v1(rep, registry, corpus)
    check_v2(rep, registry, corpus)
    check_v3(rep, corpus)
    check_v4(rep, corpus)
    check_trace_sync(rep, registry)

    counts = {
        "S1": sum(1 for f in rep.failures if f.startswith("[S1]")),
        "S2": sum(1 for f in rep.failures if f.startswith("[S2]")),
        "S3": sum(1 for f in rep.failures if f.startswith("[S3]")),
        "V1": sum(1 for f in rep.failures if f.startswith("[V1]")),
        "V2": sum(1 for f in rep.failures if f.startswith("[V2]")),
        "V3": sum(1 for f in rep.failures if f.startswith("[V3]")),
        "V4": sum(1 for f in rep.failures if f.startswith("[V4]")),
        "TRACE": sum(1 for f in rep.failures if f.startswith("[TRACE]")),
    }

    if rep.failures:
        print(f"FAIL — 结构性 fitness function 未通过，共 {len(rep.failures)} 项：")
        for f in rep.failures:
            print(f"  - {f}")
        print("\n统计: " + ", ".join(f"{k}={v}" for k, v in counts.items() if v))
        return 1

    print("PASS — 结构性 fitness function 全部通过")
    print("  检查项: S1 一个元素一个模块 · S2 扩展永不删除/权威边界 · S3 ADR docstring 可追溯性")
    print("          V1 fit criterion 测试覆盖 · V2 不变量反例覆盖 · V3 测试引用 REQ/INV")
    print("          V4 跨轮次无回归 · TRACE 追踪矩阵同步")
    print(f"  测试模块 {len(corpus)} 个: {', '.join(sorted(corpus))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
