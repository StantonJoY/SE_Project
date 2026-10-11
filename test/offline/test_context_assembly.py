"""上下文装配与 token 预算的离线测试。

Verifies: REQ-ADS-NFR-COST-001（token 预算 + 压缩后重注入）、
          INV-ADS-014（上下文预算绝不被突破；standing constraints 绝不因压缩而消失）。
批准：docs/test-approvals.yaml 的 TA-0002（按 docs/plans/P4-selector.md §4 预先批准）。
运行：仓库根目录下 pytest test/offline/test_context_assembly.py
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from selector import (
    LAYER_NAMES,
    BudgetMode,
    CandidateBrief,
    ContextAssembler,
    count_tokens,
    route_budget,
)
from selector.context import HISTORY_NOT_APPLICABLE, REINJECTION_MARKER

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config.yaml"


def briefs(n: int) -> list[CandidateBrief]:
    return [CandidateBrief(f"ad_{i:03d}", f"标题{i}", "retail", ("student",)) for i in range(1, n + 1)]


def assemble(n_candidates: int, budget: int):
    return ContextAssembler(budget_tokens=budget, summarize_candidates=5).assemble(
        "night/mobile/student", briefs(n_candidates), "选一条广告"
    )


# ---- REQ-ADS-NFR-COST-001：三档路由 ----

def test_route_budget_three_tiers() -> None:
    """REQ-ADS-NFR-COST-001：route_budget 必须是确定性的三档路由（DIRECT/SUMMARIZE/OVER_BUDGET）。"""
    budget, ratio = 1000, 0.85
    assert route_budget(0, budget, threshold_ratio=ratio).mode is BudgetMode.DIRECT
    assert route_budget(850, budget, threshold_ratio=ratio).mode is BudgetMode.DIRECT  # 恰在阈值
    assert route_budget(851, budget, threshold_ratio=ratio).mode is BudgetMode.SUMMARIZE
    assert route_budget(1000, budget, threshold_ratio=ratio).mode is BudgetMode.SUMMARIZE  # 恰在上限
    assert route_budget(1001, budget, threshold_ratio=ratio).mode is BudgetMode.OVER_BUDGET


def test_route_budget_rejects_non_positive_budget() -> None:
    """REQ-ADS-NFR-COST-001：预算非正数属配置错误，必须显式拒绝而非静默按 0 处理。"""
    try:
        route_budget(10, 0)
    except ValueError as e:
        assert "budget" in str(e)
    else:  # pragma: no cover
        raise AssertionError("budget=0 应抛 ValueError")


def test_compaction_threshold_is_85_percent() -> None:
    """REQ-ADS-NFR-COST-001：compaction 阈值必须为预算的 85%（课程 §8.4 P165）。"""
    d = route_budget(100, 2000)
    assert d.compaction_threshold == 1700
    assert d.compaction_threshold == int(2000 * 0.85)


# ---- 六层结构 ----

def test_six_layers_all_present() -> None:
    """INV-ADS-014：六层必须**全部**存在（含 HISTORY），不得默默省略任何一层。"""
    ctx = assemble(3, 2000)
    assert tuple(ctx.layers) == LAYER_NAMES
    assert set(ctx.layers) == set(LAYER_NAMES)


def test_history_layer_explicitly_marked_not_applicable() -> None:
    """INV-ADS-014：V1 无状态 ⇒ HISTORY 层为空，但必须**显式标注不适用 + 理由**。

    显式声明的理由：省略会让后来者误以为忘了做，显式声明才让"这是一个决定"可被审计
    （docs/architecture/memory-design.md §4 M3）。
    """
    ctx = assemble(3, 2000)
    assert ctx.layers["HISTORY"] == HISTORY_NOT_APPLICABLE
    assert "不适用" in ctx.layers["HISTORY"]


# ---- 预算与压缩 ----

def test_assembled_tokens_within_budget_when_direct() -> None:
    """INV-ADS-014：DIRECT 档下装配结果必须落在预算内。"""
    ctx = assemble(3, 2000)
    assert not ctx.compacted
    assert ctx.tokens <= 2000
    assert ctx.tokens == count_tokens(ctx.prompt)


def test_compaction_triggers_in_summarize_tier() -> None:
    """INV-ADS-014：候选规模使估算落在 (阈值, 预算] 时，必须触发 compression（SUMMARIZE 档）。

    档位边界由实测确定（预算 2000、阈值 1700、约 13.5 token/候选）：
    115 候选估算 1706 token → SUMMARIZE；140 候选估算 2056 → OVER_BUDGET。
    """
    ctx = assemble(115, 2000)
    assert ctx.compacted, f"应触发 compaction；决策={ctx.decisions}"
    assert any("SUMMARIZE" in d for d in ctx.decisions)
    # 压缩后规模应显著回落
    assert ctx.tokens < 2000


def test_compaction_reinjects_standing_constraints() -> None:
    """INV-ADS-014（反例）：compaction 后 **standing constraints 必须仍在最终 prompt 中**。

    这是本模块的安全要害 —— 课程 P165 实测 compaction 会把 Instructions 推到
    低注意力位置，导致"规则存在但不可见"（约束满足率 98% → 72%）。
    若本测试失败，说明压缩把约束挤掉了，属不变量违例。
    """
    ctx = assemble(115, 2000)
    assert ctx.compacted, "前置条件：本场景应触发 compaction"
    # ① 约束文本仍在层 2
    assert REINJECTION_MARKER in ctx.layers["INSTRUCTIONS"]
    # ② 且确实出现在**最终 prompt** 中（而非仅存于 layers 字段）
    assert REINJECTION_MARKER in ctx.prompt
    # ③ 决策记录必须留痕（可审计）
    assert any("RE-INJECT" in d for d in ctx.decisions)
    # ④ 闭集约束的实质内容仍在
    assert "只能从候选列表中选择 ad_id" in ctx.prompt


def test_never_trimmed_layers_survive_heavy_compaction() -> None:
    """INV-ADS-014：SYSTEM 与 INSTRUCTIONS 属"永不裁剪"层，极端压缩后仍须非空。"""
    ctx = assemble(135, 2000)  # 仍在 SUMMARIZE 档的极端值
    assert ctx.compacted
    assert ctx.layers["SYSTEM"].strip()
    assert ctx.layers["INSTRUCTIONS"].strip()


def test_over_budget_is_recorded_for_upper_layer() -> None:
    """REQ-ADS-NFR-COST-001：即使压缩仍超预算时，必须在决策记录中留痕（供上层降级 no_ad）。"""
    ctx = assemble(300, 2000)  # 候选规模远超预算 → OVER_BUDGET
    assert ctx.tokens > 0
    assert any("OVER_BUDGET" in d for d in ctx.decisions), ctx.decisions


# ---- 五步管线 ----

def test_pipeline_deduplicates_candidates() -> None:
    """INV-ADS-014（步骤 DEDUPLICATE）：重复候选必须被去除，且留痕。"""
    dup = briefs(2) + briefs(2)  # ad_001,ad_002,ad_001,ad_002
    ctx = ContextAssembler(budget_tokens=2000).assemble("s", dup, "t")
    assert any("DEDUPLICATE" in d for d in ctx.decisions)
    assert ctx.layers["RETRIEVED"].count("ad_001") == 1


def test_pipeline_prioritizes_deterministically() -> None:
    """REQ-ADS-ARCH-004：候选须按 ad_id 升序重排，使装配结果与输入顺序无关。"""
    a = ContextAssembler(budget_tokens=2000).assemble("s", briefs(3), "t")
    b = ContextAssembler(budget_tokens=2000).assemble("s", list(reversed(briefs(3))), "t")
    assert a.layers["RETRIEVED"] == b.layers["RETRIEVED"]


def test_assembly_is_deterministic() -> None:
    """REQ-ADS-ARCH-004：同一输入重复装配必须逐位一致。"""
    first = assemble(50, 2000)
    assert all(assemble(50, 2000).prompt == first.prompt for _ in range(3))


def test_count_tokens_is_pure_and_monotonic() -> None:
    """REQ-ADS-ARCH-004：count_tokens 为纯函数且对更长的文本给出不小于的估算。"""
    assert count_tokens("") == 0
    assert count_tokens("abc") == count_tokens("abc")
    assert count_tokens("a" * 30) > count_tokens("a" * 3)


# ---- 与 config.yaml 的同步（防止 OQ-004/预算静默漂移） ----

def test_config_threshold_matches_confirmed_decision() -> None:
    """REQ-ADS-NFR-SAFETY-005：config.yaml 的 confidence 阈值必须仍为 OQ-004 的定案值 0.5。

    目的：若有人改了阈值却没同步需求记录（docs/req/requirements.yaml 的 OQ-004 resolution），
    本测试失败 —— 使"配置与决策记录漂移"变得可见。
    """
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert cfg["selector"]["confidence_threshold"] == 0.5


def test_default_budget_constant_matches_requirement() -> None:
    """REQ-ADS-NFR-COST-001：本模块默认 token 预算须与需求登记的 2000 一致。"""
    reg = yaml.safe_load(
        (ROOT / "docs" / "req" / "requirements.yaml").read_text(encoding="utf-8")
    )
    req = next(r for r in reg["baseline_requirements"] if r["id"] == "REQ-ADS-NFR-COST-001")
    assert ContextAssembler().budget_tokens == req["metric"]["threshold"]
    # 顺带校验估算函数与 REINJECTION 标记未被改名（它们是外部可依赖的公开常量）
    assert re.fullmatch(r"约束（不可协商）：", REINJECTION_MARKER)
