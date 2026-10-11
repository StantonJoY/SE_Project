#!/usr/bin/env python3
"""变异验证（mutation verification）—— 证明测试**具备证伪能力**（ASR-ADS-16 / INV-ADS-011）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\mutation_check.py
    .venv\\Scripts\\python.exe scripts\\mutation_check.py --only INV-ADS-001
    .venv\\Scripts\\python.exe scripts\\mutation_check.py --list

**它回答的问题**：覆盖表里声明 `negative_test_backed: true` 的每条不变量，
其"反例测试"**真的会在实现被破坏时失败吗**？

对每条已声明的不变量，本脚本：
  1. 按 `MUTATIONS` 表把某个函数**变异**为违反该不变量的版本；
  2. 在**子进程**中运行该不变量对应的测试子集；
  3. 断言测试**确实失败**。
  若注入违规后测试**仍然全绿** → 该"反例测试"不具备证伪能力 → 本脚本 FAIL。

**两条安全性设计**
  · **绝不修改仓库源文件**：变异通过 pytest 插件在**内存中** monkeypatch 实现。
    子进程退出即消失，不存在"改坏源码忘了还原"的风险。
  · **补丁目标必须是调用方绑定**：例如 `app.pipeline.parse_llm_output`
    而非 `selector.parser.parse_llm_output` —— 因为管道在导入时已取得函数引用。
    打错目标会导致补丁无效、变异**假通过**（这正是本脚本要防的失效模式，
    故在 `MUTATIONS` 中为每条显式写明目标与理由）。

退出码：0 = 每条不变量都被证伪；1 = 存在"注入违规但测试仍全绿"的不变量。
"""

from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
COVERAGE_MAP = ROOT / "docs" / "code-governance" / "acceptance-coverage-map.yaml"

# 子进程加载 `scripts/mutation_check.py` 作为 pytest 插件（`-p mutation_check`），
# 由环境变量 MUTATION_ID 选择要注入的变异。故 PYTHONPATH 必须含 `scripts/`。
PLUGIN_ID = "mutation_check"


@dataclass(frozen=True)
class Mutation:
    """一条变异：把 target 替换为 replacement，使对应不变量被违反。"""

    invariant: str
    mutation_id: str
    description: str
    target: str            # "module:qualname"
    replacement: str       # 求值为替换对象的 Python 表达式
    tests: tuple[str, ...]  # 期望**失败**的测试节点
    why_bound_here: str    # 为何补丁打在这个目标上（防"补丁打错导致假通过"）


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        invariant="INV-ADS-001",
        mutation_id="MUT-CATEGORY-PASS",
        description="把合规的品类黑名单检查变异为**恒通过**（放开 medical/financial/adult）",
        target="compliance.pipeline:check_category",
        replacement="lambda ad, rules: _APPROVED",
        tests=(
            "test/offline/test_app_pipeline.py::test_degrade_compliance_rejected",
            "test/offline/test_compliance.py::test_check_category_reject_financial",
        ),
        why_bound_here="管道调用 compliance.pipeline 模块属性，故打在模块上即可生效",
    ),
    Mutation(
        invariant="INV-ADS-002",
        mutation_id="MUT-OUTPUT-PASS",
        description="把合规的候选集存在性检查变异为**恒通过**（放开集外 ad_id）",
        target="compliance.pipeline:check_output",
        replacement="lambda ad, candidates: _APPROVED",
        tests=(
            "test/offline/test_compliance.py::test_check_output_reject_not_in_candidates",
        ),
        why_bound_here="同上：管道按模块属性调用 check_output",
    ),
    Mutation(
        invariant="INV-ADS-003",
        mutation_id="MUT-PARSE-BYPASS",
        description="把严格 JSON 解析变异为**绕过校验**（畸形输出也当作合法）",
        target="app.pipeline:parse_llm_output",
        replacement="lambda raw, candidate_ids: _JUDGMENT",
        tests=(
            "test/offline/test_app_pipeline.py::test_degrade_llm_output_invalid_after_retry",
        ),
        why_bound_here=(
            "**必须是 app.pipeline**：管道在 `from selector import parse_llm_output` 时"
            "已取得函数引用，补丁打在 selector.parser 上不会影响管道 → 会对变异免疫、假通过"
        ),
    ),
    Mutation(
        invariant="INV-ADS-004",
        mutation_id="MUT-EXPLANATION-PASS",
        description="把解释校验变异为**恒通过**（违禁解释不再被剥离）",
        target="selector:verify_explanation",
        replacement='lambda explanation, banned_words: _VERDICT',
        tests=(
            "test/offline/test_app_pipeline.py::test_explanation_banned_word_is_stripped_in_pipeline",
        ),
        why_bound_here=(
            "必须打**包级** `selector.verify_explanation`：`selector/__init__.py` 重导出了该名称，"
            "测试导入的是包级绑定，补丁打在 `selector.explanation` 上不会影响它 → 假通过。"
            "另：原选的 test_explanation.py 直调该函数，与本变异目标一致但**未覆盖管道接线**，"
            "故改为管道级测试，同时验证「解释降级不影响 ad_id」"
        ),
    ),
    Mutation(
        invariant="INV-ADS-005",
        mutation_id="MUT-INJECTION-CLEAN",
        description="把 pre-model 注入门变异为**恒判干净**（注入可抵达 LLM）",
        target="app.sanitize:scan_for_injection + app.pipeline:scan_for_injection",
        replacement="lambda text: _clean()",
        tests=(
            "test/offline/test_app_pipeline.py::test_poisoned_material_is_rejected_by_pipeline",
        ),
        why_bound_here=(
            "**必须打两处**：① `app.sanitize`（定义模块，供直调该函数的测试）；"
            "② `app.pipeline`（**导入引用**，管道在 import 时已固定绑定，"
            "只改定义模块对它无效 → 假通过）。这是本脚本最易踩的坑，故显式写出"
        ),
    ),
    Mutation(
        invariant="INV-ADS-006",
        mutation_id="MUT-CONFIDENCE-HIGH",
        description="把解析出的 confidence 变异为**恒为 1.0**（低置信度永远过阈值）",
        target="app.pipeline:parse_llm_output",
        replacement="lambda raw, candidate_ids: _HIGH_CONF",
        tests=(
            "test/offline/test_app_pipeline.py::test_degrade_low_confidence",
        ),
        why_bound_here="管道持有 parse_llm_output 的导入引用",
    ),
    Mutation(
        invariant="INV-ADS-007",
        mutation_id="MUT-BANNED-PASS",
        description="把违禁词检查变异为**恒通过**（违禁文案可展示）",
        target="compliance.pipeline:check_banned_words",
        replacement="lambda ad, banned_words: _APPROVED",
        tests=(
            "test/offline/test_banned_words.py::test_every_banned_word_is_actually_blocked",
        ),
        why_bound_here="该测试直接调用违禁词检查，故打在 compliance.pipeline 上即生效",
    ),
    Mutation(
        invariant="INV-ADS-008",
        mutation_id="MUT-SCENE-PASS",
        description="把规则级场景检查变异为**恒通过**（夜间 gaming / 校园 adult 可展示）",
        target="compliance.pipeline:check_scene",
        replacement="lambda ad, scene, rules: _APPROVED",
        tests=(
            "test/offline/test_compliance.py::test_check_scene_night_gaming",
        ),
        why_bound_here="管道与测试均按模块属性调用 check_scene",
    ),
    Mutation(
        invariant="INV-ADS-012",
        mutation_id="MUT-AUDIT-GUARD-OFF",
        description="去掉「恰好 1 条」的守卫（允许同一请求写多条审计）",
        target="audit.store:AuditRecordBuilder.write",
        replacement="_write_unguarded",
        tests=(
            "test/offline/test_audit.py::test_second_write_is_rejected",
        ),
        why_bound_here="直接替换构造器方法，使二次写入不再抛错",
    ),
    Mutation(
        invariant="INV-ADS-013",
        mutation_id="MUT-RAISE-INSTEAD-OF-DEGRADE",
        description="把「总是返回结构化结果」变异为**抛异常**（失败不再降级）",
        target="app.pipeline:recommend",
        replacement="_recommend_raises",
        tests=(
            "test/offline/test_app_pipeline.py::test_pipeline_never_raises_on_bad_input",
        ),
        why_bound_here=(
            "测试通过 `from app import recommend` 调用（包级绑定）；`app/__init__.py` 重导出了它。"
            "因此**同时**补丁 `app.pipeline.recommend` 与包级 `app.recommend`，两者都要打"
        ),
    ),
    Mutation(
        invariant="INV-ADS-014",
        mutation_id="MUT-NO-REINJECT",
        description="去掉 compaction 后的**约束重注入**（压缩即可让约束消失）",
        target="selector.context:_Assembler.build_layers",
        replacement="_build_layers_without_reinject",
        tests=(
            "test/offline/test_context_assembly.py::test_compaction_reinjects_standing_constraints",
        ),
        why_bound_here="测试直接构造 ContextAssembler（该类内部引用本方法）",
    ),
    Mutation(
        invariant="INV-ADS-016",
        mutation_id="MUT-GATE-ALWAYS-PASS",
        description="把评估门的判定变异为**恒通过**（阈值失败不再阻断）",
        target="eval.eval_runner:ReplayReport.passed",
        replacement="_report_always_passed",
        tests=(
            "test/offline/test_eval_runner.py::test_exit_code_reflects_threshold",
        ),
        why_bound_here=(
            "**必须打两个模块名**：`eval/eval_runner.py` 会被导入成两个不同的模块对象 —— "
            "`eval.eval_runner` 与 `eval_runner`（后者源于测试文件把 `eval/` 加入 sys.path），"
            "两者的 `ReplayReport` 不是同一个类对象；只替一个会假通过。"
            "本变异针对**评估门自身**：门禁若恒判通过，则 INV-ADS-016 名存实亡"
        ),
    ),
    Mutation(
        invariant="INV-ADS-015",
        mutation_id="MUT-DETERMINISM-BREAK",
        description="破坏确定性：让解析结果带**随机 confidence**",
        target="selector:parse_llm_output",
        replacement="lambda raw, candidate_ids: _nondeterministic()",
        tests=(
            "test/offline/test_selector.py::test_parse_is_deterministic",
        ),
        why_bound_here=(
            "必须打**包级** `selector.parse_llm_output`：测试写的是 "
            "`from selector import parse_llm_output`（包级绑定），"
            "补丁打在 `selector.parser` 上对它无效 → 假通过"
        ),
    ),
)


# --------------------------------------------------------------------------
# 变异载荷（真正的函数定义，供 pytest 插件注入）
#
# ⚠️ **这些函数定义在本模块（脚本）里，不在 exec 字符串里** —— 这是刻意的：
#   替换用的 lambda 若定义在 exec 出来的命名空间中，其 `__globals__` 指向该命名空间，
#   而它引用的 `_clean` / `_verdict` 等定义在本模块，解析会抛 NameError，
#   使测试因**无关原因**失败或通过（假象）。定义在同处即可消除该陷阱。
# --------------------------------------------------------------------------

def _approved():
    """合规检查的「恒通过」返回值。"""
    from compliance.models import CheckResult
    return CheckResult.ok()


def _judgment():
    """绕过解析校验：返回一个合法判断（使畸形输出也被接受）。"""
    from selector.types import OutputJudgment
    return OutputJudgment(ad_id="ad_001", reason="mutated", confidence=0.99)


def _high_conf():
    """把 confidence 恒定抬高到 1.0（低置信度永远过阈值）。"""
    from selector.types import OutputJudgment
    return OutputJudgment(ad_id="ad_001", reason="mutated-high-conf", confidence=1.0)


def _nondeterministic():
    """破坏确定性：confidence 随机。"""
    from selector.types import OutputJudgment
    return OutputJudgment(ad_id="ad_001", reason="mutated", confidence=random.random())


def _clean():
    """注入门恒判干净。"""
    from app.sanitize import SanitizeResult
    return SanitizeResult(clean=True)


def _verdict():
    """解释校验恒判 ok（违禁解释不再被剥离）。"""
    from selector.explanation import ExplanationVerdict
    return ExplanationVerdict(verdict="ok", text="(mutated: not verified)", reason_code="ok")


def _write_unguarded(self, **kwargs):
    """去掉 `_written` 守卫 —— 允许同一请求写第二条审计。"""
    from datetime import datetime, timezone
    self.fields.update(kwargs)
    record = {
        "audit_id": self.audit_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **self.fields,
    }
    self.store.append(record)
    self._written = True
    return self.audit_id


def _recommend_raises(*args, **kwargs):
    """把「总是返回结构化结果」变异为抛异常。"""
    raise RuntimeError("mutated: 不再降级，直接抛异常")


def _report_always_passed(self) -> bool:  # noqa: ARG001
    """把评估门的判定变异为**恒通过**（阈值与违规都不再阻断）。"""
    return True


def _build_layers_without_reinject(self, scene_summary, candidates, task, total_candidates):
    """删掉重注入分支 —— 压缩后 standing constraints 不再回到层 2。"""
    from selector.client import briefs_to_prompt_block
    from selector.context import (
        HISTORY_NOT_APPLICABLE,
        LAYER_HISTORY,
        LAYER_INSTRUCTIONS,
        LAYER_RETRIEVED,
        LAYER_STATE,
        LAYER_SYSTEM,
        LAYER_USER,
        STANDING_CONSTRAINTS,
        SYSTEM_PROMPT,
    )
    block = briefs_to_prompt_block(candidates)
    self.layers[LAYER_SYSTEM] = SYSTEM_PROMPT
    self.layers[LAYER_INSTRUCTIONS] = STANDING_CONSTRAINTS
    self.layers[LAYER_RETRIEVED] = block or "（无候选）"
    self.layers[LAYER_HISTORY] = HISTORY_NOT_APPLICABLE
    self.layers[LAYER_STATE] = f"[场景] {scene_summary}"
    self.layers[LAYER_USER] = task
    # 刻意不做重注入


# 具名 lambda：定义在本模块，故其 __globals__ 能解析上面的辅助函数
_clean_lambda = lambda text: _clean()                                # noqa: E731
_verdict_lambda = lambda explanation, banned_words: _verdict()       # noqa: E731
_nondet_lambda = lambda raw, candidate_ids: _nondeterministic()      # noqa: E731

_PAYLOAD_HELPERS = (
    "_approved", "_judgment", "_high_conf", "_nondeterministic", "_clean",
    "_verdict", "_write_unguarded", "_recommend_raises", "_build_layers_without_reinject",
)

PLUGIN_SOURCE = '''
"""pytest 插件：按 MUTATION_ID 在内存中注入一条变异（不修改任何源文件）。"""
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

MUTANT = os.environ.get("MUTATION_ID", "")


def _approved():
    from compliance.models import CheckResult
    return CheckResult.ok()


def _judgment():
    from selector.types import OutputJudgment
    return OutputJudgment(ad_id="ad_001", reason="mutated", confidence=0.99)


def _high_conf():
    from selector.types import OutputJudgment
    return OutputJudgment(ad_id="ad_001", reason="mutated-high-conf", confidence=1.0)


def _nondeterministic():
    from selector.types import OutputJudgment
    return OutputJudgment(ad_id="ad_001", reason="mutated", confidence=random.random())


def _clean():
    from app.sanitize import SanitizeResult
    return SanitizeResult(clean=True)


def _verdict():
    from selector.explanation import ExplanationVerdict
    return ExplanationVerdict(verdict="ok", text="(mutated: not verified)", reason_code="ok")


def _write_unguarded(self, **kwargs):
    """去掉 _written 守卫 —— 允许写第二条。"""
    self.fields.update(kwargs)
    from datetime import datetime, timezone
    record = {"audit_id": self.audit_id,
              "timestamp": datetime.now(timezone.utc).isoformat(), **self.fields}
    self.store.append(record)
    self._written = True
    return self.audit_id


def _recommend_raises(*args, **kwargs):
    raise RuntimeError("mutated: 不再降级，直接抛异常")


def _build_layers_without_reinject(self, scene_summary, candidates, task, total_candidates):
    """删掉重注入分支 —— 压缩后约束不再回到层 2。"""
    from selector.client import briefs_to_prompt_block
    from selector.context import (
        HISTORY_NOT_APPLICABLE, LAYER_HISTORY, LAYER_INSTRUCTIONS, LAYER_RETRIEVED,
        LAYER_STATE, LAYER_SYSTEM, LAYER_USER, STANDING_CONSTRAINTS, SYSTEM_PROMPT,
    )
    block = briefs_to_prompt_block(candidates)
    self.layers[LAYER_SYSTEM] = SYSTEM_PROMPT
    self.layers[LAYER_INSTRUCTIONS] = STANDING_CONSTRAINTS
    self.layers[LAYER_RETRIEVED] = block or "（无候选）"
    self.layers[LAYER_HISTORY] = HISTORY_NOT_APPLICABLE
    self.layers[LAYER_STATE] = f"[场景] {scene_summary}"
    self.layers[LAYER_USER] = task
    # 刻意不做重注入
'''

# 变异表：每条给出 **全部** 需要替换的绑定。
# ⚠️ 同一函数可能有多个绑定（定义模块 / 导入引用 / 包级重导出），
#    只替其中一个会让变异**假通过**。故此处一律显式列出所有绑定。
REPLACEMENTS: dict[str, list[tuple[str, str, object]]] = {
    # compliance 包内各检查：管道与测试均按模块属性调用
    "MUT-CATEGORY-PASS": [("compliance.pipeline", "check_category", _approved)],
    "MUT-OUTPUT-PASS": [("compliance.pipeline", "check_output", _approved)],
    "MUT-BANNED-PASS": [("compliance.pipeline", "check_banned_words", _approved)],
    "MUT-SCENE-PASS": [("compliance.pipeline", "check_scene", _approved)],
    # 管道持有导入引用 → 必须打 app.pipeline
    "MUT-PARSE-BYPASS": [("app.pipeline", "parse_llm_output", _judgment)],
    "MUT-CONFIDENCE-HIGH": [("app.pipeline", "parse_llm_output", _high_conf)],
    # 包级重导出的名称（selector/__init__ 与 app/__init__）→ 打包与定义模块
    "MUT-EXPLANATION-PASS": [
        ("selector", "verify_explanation", _verdict_lambda),
        ("selector.explanation", "verify_explanation", _verdict_lambda),
    ],
    "MUT-DETERMINISM-BREAK": [
        ("selector", "parse_llm_output", _nondet_lambda),
        ("selector.parser", "parse_llm_output", _nondet_lambda),
    ],
    "MUT-INJECTION-CLEAN": [
        ("app.sanitize", "scan_for_injection", _clean_lambda),
        ("app.pipeline", "scan_for_injection", _clean_lambda),
    ],
    "MUT-RAISE-INSTEAD-OF-DEGRADE": [
        ("app.pipeline", "recommend", _recommend_raises),
        ("app", "recommend", _recommend_raises),
    ],
    "MUT-AUDIT-GUARD-OFF": [("audit.store", "AuditRecordBuilder.write", _write_unguarded)],
    "MUT-NO-REINJECT": [
        ("selector.context", "_Assembler.build_layers", _build_layers_without_reinject),
    ],
    # 评估门自身：property 替换即可（测试直接读 report.passed）
    # ⚠️ **必须打两个模块名**：`eval/eval_runner.py` 会被导入成两个**不同**的模块对象 ——
    #    · `eval.eval_runner`（replay 时经 `import eval.eval_runner`）
    #    · `eval_runner`（测试文件把 `eval/` 加入 sys.path 后 `from eval_runner import ...`）
    # 两者的 `ReplayReport` **不是同一个类对象**，只替一个即假通过。
    "MUT-GATE-ALWAYS-PASS": [
        ("eval.eval_runner", "ReplayReport.passed", property(_report_always_passed)),
        ("eval_runner", "ReplayReport.passed", property(_report_always_passed)),
    ],
}


def pytest_configure(config) -> None:  # noqa: ARG001
    """pytest 插件入口（子进程以 `-p mutation_check` 加载）。

    直接在本进程内替换 `REPLACEMENTS` 中登记的**全部**绑定，不做任何 exec ——
    替换对象都是本模块的具名函数/具名 lambda，其 `__globals__` 即本模块，
    故不存在"名字解析不到"的陷阱。
    """
    import importlib

    mutant = os.environ.get("MUTATION_ID")
    if not mutant:
        return
    if mutant not in REPLACEMENTS:
        raise SystemExit(f"未知 MUTATION_ID: {mutant}")
    for mod_name, attr, replacement in REPLACEMENTS[mutant]:
        mod = importlib.import_module(mod_name)
        parts = attr.split(".")
        host = mod
        for p in parts[:-1]:
            host = getattr(host, p)
        if not hasattr(host, parts[-1]):
            raise SystemExit(f"变异目标不存在: {mod_name}:{attr}")
        setattr(host, parts[-1], replacement)
        print(f"[mutation] 已注入 {mutant} → {mod_name}:{attr}", flush=True)


# --------------------------------------------------------------------------
# 运行
# --------------------------------------------------------------------------

@dataclass
class MutationResult:
    mutation: Mutation
    detected: bool
    returncode: int
    output: str = ""
    note: str = field(default="")


def _declared_invariants() -> list[str]:
    """从覆盖表读取声明 `negative_test_backed: true` 的不变量。"""
    import yaml

    data = yaml.safe_load(COVERAGE_MAP.read_text(encoding="utf-8"))
    return [i["id"] for i in data["invariants"] if i.get("negative_test_backed")]


def _classify(returncode: int, output: str) -> tuple[bool, str]:
    """判定一次变异运行是否构成「被检出」。

    返回 `(detected, note)`。

    **必须同时满足**才算被检出：
      ① 输出含注入标记 `[mutation]` —— 否则变异根本没生效，结果不可信；
      ② 退出码非零，且**不是** 4（pytest 用法/收集错误 —— 插件自身写错的情形）。

    抽成独立函数是为了让它**可被测试**：本脚本开发中真实踩过"假检出"，
    故该判定逻辑本身需要回归保护。
    """
    if "[mutation]" not in output:
        return False, "⚠️ 变异未被注入（插件未生效）—— 结果不可信，**不计为被检出**"
    if returncode == 4:
        return False, "⚠️ pytest 退出码 4（用法/收集错误）—— 不计为被检出"
    return returncode != 0, ""


def run_mutation(mut: Mutation, *, python: str, plugin_path: Path) -> MutationResult:
    """在子进程中注入变异并运行目标测试；测试**失败**即算「被检出」。"""
    env = dict(os.environ)
    env["MUTATION_ID"] = mut.mutation_id
    env["PYTHONPATH"] = os.pathsep.join(
        [str(SRC), str(ROOT / "scripts"), str(ROOT), env.get("PYTHONPATH", "")]
    )
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [
        python, "-m", "pytest", "-p", "mutation_check",
        "-p", "no:cacheprovider", "--no-header", "-q", "--tb=no",
        *mut.tests,
    ]
    proc = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    detected, note = _classify(proc.returncode, out)
    tail = [ln for ln in out.strip().splitlines() if ln.strip()]
    return MutationResult(
        mutation=mut, detected=detected, returncode=proc.returncode,
        output=tail[-1] if tail else "(无输出)", note=note,
    )


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="变异验证（INV-ADS-011 / ASR-ADS-16）")
    parser.add_argument("--only", help="只跑某条不变量（如 INV-ADS-001）")
    parser.add_argument("--list", action="store_true", help="只列出变异表")
    args = parser.parse_args(argv)

    if args.list:
        for m in MUTATIONS:
            print(f"{m.invariant:14s} {m.mutation_id:32s} {m.description}")
        return 0

    declared = _declared_invariants()
    covered = {m.invariant for m in MUTATIONS}
    missing = sorted(set(declared) - covered)

    print("=" * 78)
    print("变异验证：每条声明为已覆盖的不变量，其反例测试是否真会失败？")
    print("=" * 78)
    print(f"覆盖表声明 negative_test_backed: {len(declared)} 条")
    print(f"变异表覆盖:                     {len(covered)} 条")
    if missing:
        print(f"⚠️ 变异表**未覆盖**的不变量: {missing}")
    print()

    todos = [m for m in MUTATIONS if not args.only or m.invariant == args.only]
    if not todos:
        print(f"没有匹配 {args.only!r} 的变异")
        return 1

    # 把插件写到一个**可导入的名称**：scripts/mutation_check.py 本身即插件
    plugin_path = ROOT / "scripts" / "mutation_check.py"
    results: list[MutationResult] = []
    for m in todos:
        r = run_mutation(m, python=sys.executable, plugin_path=plugin_path)
        results.append(r)
        mark = "✓ 被检出" if r.detected else "✗ 未被检出"
        print(f"  {mark}  {m.invariant:14s} {m.mutation_id}")
        print(f"            变异: {m.description}")
        print(f"            测试: {r.output or '(无输出)'}")
        if r.note:
            print(f"            {r.note}")

    undetected = [r for r in results if not r.detected]
    print()
    print("=" * 78)
    if missing or undetected:
        print("FAIL — 存在不具备证伪能力的「反例测试」：")
        for inv in missing:
            print(f"  - {inv}：变异表中**没有**对应变异（未被验证）")
        for r in undetected:
            print(f"  - {r.mutation.invariant}：注入「{r.mutation.description}」后测试**仍然全绿**")
            print(f"    即该反例测试无法发现此类违规（{r.mutation.mutation_id}）")
        print()
        print("  依据：INV-ADS-011 / REQ-ADS-NFR-QA-002 ——")
        print("        每条不变量必须有一个「在违规时确实会失败」的测试。")
        return 1
    print(f"PASS — {len(results)} 条变异全部被检出：")
    print("       每条声明覆盖的不变量，其反例测试在实现被破坏时**确实失败**。")
    print("=" * 78)
    return 0


# --------------------------------------------------------------------------
# pytest 插件入口
#
# 子进程以 `-p mutation_check` 加载本模块，pytest 会自动调用上面的
# `pytest_configure`。此处**刻意不再重复定义** —— 重复定义会覆盖前者，
# 导致替换表被绕过而静默失效（本文件开发中真实踩过该坑）。
# --------------------------------------------------------------------------

if __name__ == "__main__":
    raise SystemExit(main())
