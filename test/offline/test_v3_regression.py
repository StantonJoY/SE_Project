"""V3 零回归守卫（REQ-ADS-NFR-QA-005）。

Verifies: REQ-ADS-NFR-QA-005（V1/V2 全部离线测试不得消失、套件规模不得缩水）

把「零回归」从一句声明变成可断言的检查：基线测试模块一个都不能少，
离线套件规模不得低于 V3 开工时的基数（617）。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OFFLINE = ROOT / "test" / "offline"

#: V3 开工时的 24 个离线测试模块（少一个就是回归）
BASELINE_MODULES = {
    "test_ads.py", "test_app_pipeline.py", "test_audit.py", "test_banned_words.py",
    "test_bidding_v2.py", "test_compliance.py", "test_context_assembly.py",
    "test_eval_runner.py", "test_explanation.py", "test_mutation_check.py",
    "test_pipeline_v2.py", "test_provenance.py", "test_relevance_v2.py",
    "test_render.py", "test_repo_completeness.py", "test_requirements_registry.py",
    "test_sanitize.py", "test_scene.py", "test_selector.py",
    "test_v2_boundary_regressions.py", "test_v2_eval.py", "test_v2_governance.py",
    "test_v2_mutation.py", "test_v2_settlement_boundaries.py",
}

#: V3 开工时的测试函数数（parametrize 展开前；同期 pytest 收集 617 条）
BASELINE_TEST_FUNCTIONS = 385


def test_no_baseline_test_module_removed():
    """REQ-ADS-NFR-QA-005 / INV-ADS-011：基线测试模块不得被删除或改名。"""
    present = {path.name for path in OFFLINE.glob("test_*.py")}
    missing = BASELINE_MODULES - present
    assert not missing, f"基线测试模块缺失：{sorted(missing)}（V4 跨轮次回归会失败）"


def test_offline_suite_size_not_reduced():
    """REQ-ADS-NFR-QA-005：测试函数数不得低于基线（防止用删测试的方式让套件变绿）。"""
    count = sum(
        line.lstrip().startswith("def test_")
        for path in OFFLINE.glob("test_*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
    )
    assert count >= BASELINE_TEST_FUNCTIONS, (
        f"测试函数数 {count} 低于基线 {BASELINE_TEST_FUNCTIONS}"
    )
