"""变异验证工具自身的离线测试。

Verifies: REQ-ADS-NFR-QA-002（每条不变量 ≥1 个会在违规时失败的测试）、
          INV-ADS-011（测试须具备证伪能力；缺口必须有去向）。
批准：docs/test-approvals.yaml 的 TA-0004（pre_registered，指向 docs/plans/P7-eval.md）。
运行：仓库根目录下 pytest test/offline/test_mutation_check.py

**本模块的定位**：变异脚本本身也是一个实现，它同样会错。
故它需要自己的测试 —— 尤其是"它**能报告失败**"这一点
（一个永远输出 PASS 的检查器比没有检查器更糟）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import mutation_check as mc  # noqa: E402

# ---- 变异表自身的完整性 ----

def test_mutation_table_is_non_empty() -> None:
    """INV-ADS-011：变异表不得为空（空表会让检查形同虚设）。"""
    assert len(mc.MUTATIONS) >= 10


def test_mutation_ids_are_unique() -> None:
    """INV-ADS-011：变异 ID 必须唯一（结论需可一一对应）。"""
    ids = [m.mutation_id for m in mc.MUTATIONS]
    assert len(set(ids)) == len(ids)


def test_each_invariant_has_at_most_one_mutation() -> None:
    """INV-ADS-011：同一不变量不应重复登记（重复会让"未检出"的判定含混）。"""
    invs = [m.invariant for m in mc.MUTATIONS]
    assert len(set(invs)) == len(invs)


def test_mutation_table_covers_all_negative_backed_invariants() -> None:
    """REQ-ADS-NFR-QA-002 / INV-ADS-011：**声明为已覆盖的不变量必须有对应变异**。

    这是本文件最重要的一条：它防止"覆盖表说已覆盖、变异表却没验证"的漂移 ——
    若两者不一致，覆盖表的可信度就是假的。
    """
    declared = set(mc._declared_invariants())
    covered = {m.invariant for m in mc.MUTATIONS}
    missing = sorted(declared - covered)
    assert not missing, f"以下不变量声明已覆盖但**没有**变异验证: {missing}"


def test_no_mutation_for_undeclared_invariant() -> None:
    """INV-ADS-011：反向一致性 —— 变异表不应验证未声明为已覆盖的不变量。

    （允许存在但不要求；此处只检查变异表不引用**不存在**的不变量 ID。）
    """
    import re

    text = (ROOT / "docs" / "architecture" / "invariants.md").read_text(encoding="utf-8")
    known = set(re.findall(r"INV-ADS-\d{3}", text))
    for m in mc.MUTATIONS:
        assert m.invariant in known, f"{m.mutation_id} 引用了不存在的不变量 {m.invariant}"


def test_every_mutation_targets_real_binding() -> None:
    """INV-ADS-011：每条变异的替换目标必须真实存在。

    目标不存在会导致注入失败 —— 一个静默失效的变异会给出**假检出**，
    比不检查更危险。
    """
    import importlib

    sys.path.insert(0, str(ROOT / "src"))
    for m in mc.MUTATIONS:
        entries = mc.REPLACEMENTS[m.mutation_id]
        assert entries, f"{m.mutation_id} 的替换表为空"
        for mod_name, attr, _replacement in entries:
            mod = importlib.import_module(mod_name)
            host = mod
            for part in attr.split(".")[:-1]:
                host = getattr(host, part)
            assert hasattr(host, attr.split(".")[-1]), f"目标不存在: {mod_name}:{attr}"


def test_every_mutation_has_tests_and_rationale() -> None:
    """INV-ADS-011：每条变异必须声明它会失败的测试，且说明**为何打在此处**。

    后者专门用于防"补丁打错导致假通过"—— 该失效模式在本脚本开发中真实发生过。
    """
    for m in mc.MUTATIONS:
        assert m.tests, f"{m.mutation_id} 未声明测试"
        assert all(t.startswith("test/offline/") for t in m.tests), (
            f"{m.mutation_id} 的测试路径必须位于 test/offline/"
        )
        assert m.why_bound_here.strip(), f"{m.mutation_id} 未说明补丁绑定理由"


def test_every_mutation_test_node_exists() -> None:
    """INV-ADS-011：变异声明的测试节点必须**真实存在**（否则变异无从被检出）。"""
    for m in mc.MUTATIONS:
        for node in m.tests:
            file_part = node.split("::", 1)[0]   # 节点形如 path::test_name，只校验文件部分
            assert (ROOT / file_part).exists(), f"{m.mutation_id} 的测试文件不存在: {file_part}"


# ---- 判定逻辑本身（"它能否报告失败"） ----

def test_uninjected_run_is_not_detection() -> None:
    """INV-ADS-011（反例）：**未注入变异时不得判为「被检出」**。

    理由：插件导入失败同样会产生非零退出码；若照单全收即得到**假通过**
    —— 本脚本开发中真实踩过该坑（插件 ImportError 被误判为检出）。
    """
    detected, note = mc._classify(1, "FAILED something\n2 failed")
    assert detected is False
    assert "未被注入" in note


def test_pytest_usage_error_is_not_detection() -> None:
    """INV-ADS-011（反例）：pytest 退出码 4（用法/收集错误）不得判为「被检出」。

    否则插件写错会伪装成"变异被检出"这一最坏情形。
    """
    detected, note = mc._classify(4, "[mutation] 已注入 X")
    assert detected is False
    assert "退出码 4" in note


def test_genuine_failure_is_detection() -> None:
    """INV-ADS-011：注入成功 + 测试失败 ⇒ 才算「被检出」。"""
    detected, note = mc._classify(1, "[mutation] 已注入 MUT-X\n1 failed")
    assert detected is True
    assert note == ""


def test_genuine_pass_is_not_detection() -> None:
    """INV-ADS-011（反例）：注入成功但测试**全绿** ⇒ 不具备证伪能力，必须报未检出。"""
    detected, _ = mc._classify(0, "[mutation] 已注入 MUT-X\n5 passed")
    assert detected is False


def test_declared_invariants_reads_coverage_map() -> None:
    """REQ-ADS-NFR-QA-002：`negative_test_backed` 的判定来源必须是覆盖表（单一来源）。"""
    declared = mc._declared_invariants()
    assert declared, "覆盖表应至少声明一条 negative_test_backed"
    assert all(i.startswith("INV-ADS-") for i in declared)


def test_list_mode_lists_all_mutations(capsys) -> None:
    """INV-ADS-011：`--list` 必须列出全部变异（供人工审查）。"""
    rc = mc.main(["--list"])
    captured = capsys.readouterr().out
    assert rc == 0
    for m in mc.MUTATIONS:
        assert m.mutation_id in captured


@pytest.mark.parametrize("mutation_id", [m.mutation_id for m in mc.MUTATIONS])
def test_every_replacement_entry_is_well_formed(mutation_id: str) -> None:
    """INV-ADS-011：替换表每项必须是 (模块, 属性, 可注入对象) 三元组。

    "可注入对象"包括：普通函数/方法（callable），以及 **property**
    （替换类属性时必需 —— `property` 本身不可调用，故不能用 `callable()` 判）。
    """
    for entry in mc.REPLACEMENTS[mutation_id]:
        assert len(entry) == 3
        mod_name, attr, replacement = entry
        assert isinstance(mod_name, str) and mod_name
        assert isinstance(attr, str) and attr
        assert callable(replacement) or isinstance(replacement, property), (
            f"{mutation_id}: {attr} 的替换对象既不可调用也不是 property"
        )
