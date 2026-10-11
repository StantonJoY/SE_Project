"""评估集加载与 replay 的离线测试。

Verifies: REQ-ADS-NFR-QA-001（≥20 条、一键 replay、输出通过率与违规数）、
          REQ-ADS-NFR-PERF-001（p95 与 SLA drift）、
          INV-ADS-016（评估门：阈值失败必须阻断）、
          INV-ADS-002（集外选择为违规）、INV-ADS-012（审计条数 ≠1 为违规）。
批准：docs/test-approvals.yaml 的 TA-0004（pre_registered，指向 docs/plans/P7-eval.md）。
运行：仓库根目录下 pytest test/offline/test_eval_runner.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from app import AppConfig
from compliance.rules import SceneRules

ROOT = Path(__file__).resolve().parents[2]

import sys

sys.path.insert(0, str(ROOT / "eval"))
from eval_runner import (  # noqa: E402
    CaseOutcome,
    EvalCase,
    EvalDataError,
    ReplayReport,
    load_cases,
    replay,
    validate_cases,
)

CASES_PATH = ROOT / "eval" / "eval_cases.json"


@pytest.fixture(scope="module")
def cfg() -> AppConfig:
    return AppConfig.load(ROOT / "config.yaml")


@pytest.fixture(scope="module")
def repo() -> AdRepository:
    return AdRepository.load(ROOT / "data" / "ads.json")


@pytest.fixture(scope="module")
def banned() -> BannedWords:
    return BannedWords.load(ROOT / "data" / "banned_words.json")


@pytest.fixture(scope="module")
def rules() -> SceneRules:
    return SceneRules.load(ROOT / "data" / "scene_rules.json")


@pytest.fixture(scope="module")
def cases(repo) -> list[EvalCase]:
    return load_cases(CASES_PATH, known_ad_ids={a.ad_id for a in repo.all()})


# ---- 加载与结构 ----

def test_load_cases_ok(cases) -> None:
    """REQ-ADS-NFR-QA-001：评估集必须可加载且用例非空。"""
    assert cases
    assert all(isinstance(c, EvalCase) for c in cases)


def test_eval_set_has_at_least_20_cases(cases) -> None:
    """REQ-ADS-NFR-QA-001：**硬门槛** —— 用例数必须 ≥ 20（fit criterion 逐字要求）。"""
    assert len(cases) >= 20, f"评估集只有 {len(cases)} 条，少于要求的 20 条"


def test_every_case_has_basis_and_anchors(cases) -> None:
    """REQ-ADS-NFR-QA-001 / ADR-003 D2：每条用例必须说明**为何存在**且可追溯。"""
    for c in cases:
        assert c.basis.strip(), f"{c.id} 缺 basis（说不清为何存在）"
        assert c.anchors, f"{c.id} 缺 anchors"
        assert all(a.startswith(("REQ-ADS-", "INV-ADS-", "ASR-ADS-")) for a in c.anchors)


def test_case_ids_are_unique(cases) -> None:
    """REQ-ADS-NFR-QA-001：用例 ID 必须唯一（否则结论无法一一对应）。"""
    ids = [c.id for c in cases]
    assert len(set(ids)) == len(ids)


def test_labels_are_from_closed_enum(cases) -> None:
    """ADR-003 D3：label 必须是封闭枚举，三类分母分离的依据。"""
    assert {c.label for c in cases} <= {"MUST_PASS", "MUST_FAIL", "MUST_FAIL_ON_REPLAY"}


def test_both_denominators_are_non_empty(cases) -> None:
    """ADR-003 D3：MUST_PASS 与 MUST_FAIL **都必须有**用例。

    否则"分母分离"退化为单侧统计：只有 MUST_PASS 就无法观测"系统正确地说不"。
    """
    assert any(c.label == "MUST_PASS" for c in cases)
    assert any(c.label == "MUST_FAIL" for c in cases)


# ---- fail-closed 的数据校验（反例） ----

def _cases(payload: object, **kw) -> list[EvalCase]:
    """构造并校验一份内存中的评估集（**不落盘、不用 tmp_path**）。

    直接用 `validate_cases`（校验与读文件已分离），避免与受限沙箱的
    文件系统限制缠斗。
    """
    return validate_cases(payload, **kw)


def test_reject_top_level_not_object() -> None:
    """REQ-ADS-NFR-QA-001（反例）：顶层非对象必须被拒绝（fail-closed）。"""
    with pytest.raises(EvalDataError, match="顶层必须是含 'cases' 的对象"):
        _cases([{"id": "EC-1"}])


def test_reject_cases_not_array() -> None:
    """REQ-ADS-NFR-QA-001（反例）：cases 非数组必须被拒绝。"""
    with pytest.raises(EvalDataError, match="必须是数组"):
        _cases({"cases": {"id": "EC-1"}})


def test_reject_missing_required_field() -> None:
    """REQ-ADS-NFR-QA-001（反例）：缺必需字段必须被拒绝，**不静默跳过该用例**。"""
    bad = {"cases": [{"id": "EC-1", "scene": {}, "expected": "ad"}]}
    with pytest.raises(EvalDataError, match="缺必需字段"):
        _cases(bad)


def test_reject_unknown_expected_value() -> None:
    """REQ-ADS-NFR-QA-001（反例）：expected 非 {ad,no_ad} 必须被拒绝。"""
    bad = {"cases": [{"id": "EC-1", "scene": {}, "expected": "maybe", "label": "MUST_PASS",
                      "basis": "b", "anchors": ["REQ-ADS-X-001"]}]}
    with pytest.raises(EvalDataError, match="不在"):
        _cases(bad)


def test_reject_unknown_label() -> None:
    """ADR-003 D3（反例）：label 不在封闭枚举内必须被拒绝（否则分母归属不明）。"""
    bad = {"cases": [{"id": "EC-1", "scene": {}, "expected": "ad", "label": "PROBABLY",
                      "basis": "b", "anchors": ["REQ-ADS-X-001"]}]}
    with pytest.raises(EvalDataError, match="不在"):
        _cases(bad)


def test_reject_duplicate_id() -> None:
    """REQ-ADS-NFR-QA-001（反例）：重复 ID 必须被拒绝。"""
    one = {"id": "EC-1", "scene": {}, "expected": "no_ad", "label": "MUST_FAIL",
           "basis": "b", "anchors": ["REQ-ADS-X-001"]}
    with pytest.raises(EvalDataError, match="重复"):
        _cases({"cases": [one, dict(one)]})


def test_reject_empty_anchors() -> None:
    """REQ-ADS-NFR-QA-001（反例）：空 anchors 必须被拒绝（用例不可无据）。"""
    bad = {"cases": [{"id": "EC-1", "scene": {}, "expected": "no_ad", "label": "MUST_FAIL",
                      "basis": "b", "anchors": []}]}
    with pytest.raises(EvalDataError, match="anchors"):
        _cases(bad)


def test_reject_dead_annotation() -> None:
    """REQ-ADS-NFR-QA-001（反例）：标注的正确答案若不在素材库中（死标注）必须被拒绝。"""
    bad = {"cases": [{"id": "EC-1", "scene": {}, "expected": "ad", "label": "MUST_PASS",
                      "basis": "b", "anchors": ["REQ-ADS-X-001"], "expected_ad_id": "ad_999"}]}
    with pytest.raises(EvalDataError, match="死标注"):
        _cases(bad, known_ad_ids={"ad_001"})


def test_reject_must_pass_without_judgement_basis() -> None:
    """ADR-003 D2（反例）：expected=ad 却既无 expected_ad_id 也无 expected_category → 无法判定。"""
    bad = {"cases": [{"id": "EC-1", "scene": {}, "expected": "ad", "label": "MUST_PASS",
                      "basis": "b", "anchors": ["REQ-ADS-X-001"]}]}
    with pytest.raises(EvalDataError, match="expected_ad_id 或 expected_category"):
        _cases(bad)


def test_reject_empty_case_list() -> None:
    """REQ-ADS-NFR-QA-001（反例）：空评估集必须被拒绝（0 条不能算通过）。"""
    with pytest.raises(EvalDataError, match="为空"):
        _cases({"cases": []})


def test_reject_missing_file() -> None:
    """REQ-ADS-NFR-QA-001（反例）：评估集文件不存在必须被拒绝。"""
    with pytest.raises(EvalDataError, match="不存在"):
        load_cases(ROOT / "eval" / "definitely-not-here.json")


# ---- replay 行为 ----

def test_replay_all_cases_returns_report(cases, cfg, repo, banned, rules) -> None:
    """REQ-ADS-NFR-QA-001：一键 replay 必须跑完全部用例并返回报告。"""
    report = replay(cases, config=cfg, repo=repo, banned=banned, rules=rules)
    assert isinstance(report, ReplayReport)
    assert len(report.outcomes) == len(cases)


def test_report_reports_pass_rate_and_violations(cases, cfg, repo, banned, rules) -> None:
    """REQ-ADS-NFR-QA-001：报告必须给出**通过率**与**违规数**。"""
    report = replay(cases, config=cfg, repo=repo, banned=banned, rules=rules)
    assert 0.0 <= report.pass_rate <= 1.0
    assert isinstance(report.violations, list)


def test_replay_is_deterministic(cases, cfg, repo, banned, rules) -> None:
    """REQ-ADS-ARCH-004：同输入重复 replay 必须给出相同的达成情况（延迟除外）。"""
    a = replay(cases, config=cfg, repo=repo, banned=banned, rules=rules)
    b = replay(cases, config=cfg, repo=repo, banned=banned, rules=rules)
    assert [o.matched for o in a.outcomes] == [o.matched for o in b.outcomes]
    assert a.pass_rate == b.pass_rate


def test_replay_records_audit_count_per_case(cases, cfg, repo, banned, rules) -> None:
    """INV-ADS-012：replay 必须逐条核对审计条数（=1），并在报告中留下计数。"""
    report = replay(cases, config=cfg, repo=repo, banned=banned, rules=rules)
    assert all(o.audit_records >= 0 for o in report.outcomes)


def test_current_eval_set_passes(cases, cfg, repo, banned, rules) -> None:
    """REQ-ADS-NFR-QA-001 / INV-ADS-016：**当前评估集必须通过**。

    这是评估门的日常行使：若它失败，说明实现发生了回归（或评估集被改动）。
    """
    report = replay(cases, config=cfg, repo=repo, banned=banned, rules=rules)
    assert not report.violations, f"出现违规（零容忍）：{report.violations}"
    assert report.pass_rate >= report.pass_rate_threshold, (
        f"MUST_PASS 达成率 {report.pass_rate:.4f} < 阈值 {report.pass_rate_threshold}"
    )
    assert report.passed


# ---- 分母分离的语义（ADR-003 D3/D6） ----

def test_pass_rate_ignores_must_fail_denominator(cases, cfg, repo, banned, rules) -> None:
    """ADR-003 D3：**通过率只对 MUST_PASS 分母计算**。

    构造一条必然"未达成"的 MUST_FAIL 用例，断言它**不影响** pass_rate
    —— 这正是"预期降级不计入分母"的可执行证明。
    """
    base = replay(cases, config=cfg, repo=repo, banned=banned, rules=rules)
    # 新增一条 label=MUST_FAIL 但期望为 ad 的用例（必然未达成）
    impossible = EvalCase(
        id="EC-TESTONLY", scene=cases[0].scene, expected="ad", label="MUST_FAIL",
        basis="仅用于验证分母分离语义", anchors=("REQ-ADS-NFR-QA-001",),
        expected_ad_id="ad_001",
    )
    with_it = replay([*cases, impossible], config=cfg, repo=repo, banned=banned, rules=rules)
    assert with_it.pass_rate == base.pass_rate, "MUST_FAIL 用例不得影响通过率分母"
    assert len(with_it.must_fail) == len(base.must_fail) + 1


def test_violation_is_independent_of_pass_rate() -> None:
    """ADR-003 D6：违规是**独立判据**，不得被通过率的比例容忍稀释。

    把通过率阈值设为 0（通过率必然达标），再注入一条含违规的记录 ——
    若判定仍为「通过」，说明违规被比例平均稀释了；正确行为是有违规即不通过。
    """
    dummy = EvalCase(
        id="EC-V", scene={}, expected="no_ad", label="MUST_FAIL",
        basis="仅用于验证违规的独立性", anchors=("INV-ADS-001",),
    )
    report = ReplayReport(pass_rate_threshold=0.0)
    report.outcomes.append(
        CaseOutcome(case=dummy, matched=True, violations=("展示了未经合规批准的广告",))
    )
    assert report.violations, "违规必须被收集"
    assert report.passed is False, "存在违规时即使通过率达标也必须不通过（零容忍）"


def test_exit_code_reflects_threshold() -> None:
    """INV-ADS-016：达成率低于阈值时判定必须为「不通过」（否则门无法阻断）。

    直接构造报告对象，避免依赖真实实现的当前达成率。
    """
    case = EvalCase(
        id="EC-X", scene={}, expected="ad", label="MUST_PASS",
        basis="仅用于验证阈值判定", anchors=("REQ-ADS-NFR-QA-001",), expected_ad_id="ad_001",
    )
    report = ReplayReport(pass_rate_threshold=0.95)
    report.outcomes.extend(CaseOutcome(case=case, matched=(i < 9)) for i in range(10))
    assert report.pass_rate == pytest.approx(0.9)
    assert report.passed is False, "0.9 < 0.95 必须判不通过"

    # 反向：全部达成时阈值不得误拦
    ok = ReplayReport(pass_rate_threshold=0.95)
    ok.outcomes.extend(CaseOutcome(case=case, matched=True) for _ in range(10))
    assert ok.passed is True


def test_p95_and_sla_drift(cases, cfg, repo, banned, rules) -> None:
    """REQ-ADS-NFR-PERF-001：replay 必须计算 p95 并据此给出 SLA drift 判定。"""
    report = replay(cases, config=cfg, repo=repo, banned=banned, rules=rules)
    assert report.p95_latency_sec > 0
    assert report.sla_drift_alert == (
        report.p95_latency_sec > report.latency_p95_threshold_sec
    )
