"""决策证据版本溯源的离线测试。

Verifies: REQ-ADS-AI-002（每条决策记录含 model_version + prompt_version + threshold）、
          INV-ADS-012（版本溯源随审计记录一并落盘，恰好 1 条）。
批准：docs/test-approvals.yaml 的 TA-0004（pre_registered，指向 docs/plans/P7-eval.md）。
运行：仓库根目录下 pytest test/offline/test_provenance.py

**为什么需要版本溯源**：没有它，replay 的通过率无法归因 ——
"达成率下降了"到底是实现退化、模型换了、还是阈值改了？三个都不可答。
故 AI-002 要求每条决策记录携带这三样证据。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from app import AppConfig, recommend
from app.pipeline import UNKNOWN_VERSION, _provenance
from audit import FailingAuditStore, InMemoryAuditStore
from compliance.rules import SceneRules
from selector import PROMPT_TEMPLATE_VERSION, LLMUnavailable, MockLLM

ROOT = Path(__file__).resolve().parents[2]
NIGHT: dict = {"time_slot": "night", "device": "mobile", "user_tags": ["student"]}


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


def run(cfg, repo, banned, rules, *, scene=None, client=None, store=None):
    st = store if store is not None else InMemoryAuditStore()
    rec = recommend(
        scene if scene is not None else NIGHT,
        repo=repo, banned_words=banned, rules=rules,
        client=client or MockLLM(), audit_store=st, config=cfg,
    )
    return rec, st


# ---- 三要素齐备 ----

def test_audit_record_contains_provenance(cfg, repo, banned, rules) -> None:
    """REQ-ADS-AI-002：每条决策记录必须含 `provenance` 段。"""
    _, st = run(cfg, repo, banned, rules)
    assert st.count == 1
    assert "provenance" in st.records[0]


def test_provenance_has_all_three_elements(cfg, repo, banned, rules) -> None:
    """REQ-ADS-AI-002：必须同时含 model_version + prompt_version + thresholds。"""
    _, st = run(cfg, repo, banned, rules)
    prov = st.records[0]["provenance"]
    assert prov["model_version"]
    assert prov["prompt_version"]
    assert prov["thresholds"]


def test_model_version_reflects_config(cfg, repo, banned, rules) -> None:
    """REQ-ADS-AI-002：model_version 必须反映**实际配置**（不是硬编码字符串）。"""
    _, st = run(cfg, repo, banned, rules)
    prov = st.records[0]["provenance"]
    assert cfg.llm.provider in prov["model_version"]


def test_prompt_template_version_constant_exists() -> None:
    """REQ-ADS-AI-002：prompt 模板版本必须是**代码中的显式常量**（可被引用与追溯）。"""
    assert PROMPT_TEMPLATE_VERSION
    assert isinstance(PROMPT_TEMPLATE_VERSION, str)


def test_prompt_version_matches_constant(cfg, repo, banned, rules) -> None:
    """REQ-ADS-AI-002：审计记录的 prompt_version 必须等于上下文模板的版本常量。"""
    _, st = run(cfg, repo, banned, rules)
    assert st.records[0]["provenance"]["prompt_version"] == PROMPT_TEMPLATE_VERSION


def test_thresholds_record_the_deciding_values(cfg, repo, banned, rules) -> None:
    """REQ-ADS-AI-002：阈值段必须记录**实际影响本次决策**的值。"""
    _, st = run(cfg, repo, banned, rules)
    th = st.records[0]["provenance"]["thresholds"]
    assert th["confidence_threshold"] == cfg.selector.confidence_threshold
    assert th["context_budget_tokens"] == cfg.selector.context_budget_tokens
    assert th["llm_timeout_sec"] == cfg.llm.timeout_sec
    assert th["max_retries"] == cfg.selector.max_retries


def test_thresholds_come_from_config_not_hardcoded(cfg) -> None:
    """REQ-ADS-AI-002（反例）：改了配置，阈值证据必须跟着变 —— 证明它不是硬编码。

    这是"配置单一来源"在**证据层**的验证：若 provenance 里写死 0.5，
    改配置后证据就会撒谎。
    """
    from dataclasses import replace

    modified = replace(cfg, selector=replace(cfg.selector, confidence_threshold=0.77))
    prov = _provenance(modified)
    assert prov["thresholds"]["confidence_threshold"] == 0.77
    assert prov["thresholds"]["confidence_threshold"] != cfg.selector.confidence_threshold


# ---- 降级路径同样要有溯源 ----

def test_provenance_present_on_degradation_paths(cfg, repo, banned, rules) -> None:
    """REQ-ADS-AI-002 / INV-ADS-012：**降级路径也必须带版本溯源**。

    理由：`no_ad` 同样是决策（"不展示"也是结论），它也需可归因 ——
    否则无法回答"这次降级是因为换了模型还是因为规则变了"。
    """
    cases = [
        ("scene_invalid", {"time_slot": "midnight", "device": "mobile"}, MockLLM()),
        ("low_confidence", NIGHT, MockLLM(confidence=0.1)),
        ("llm_error", NIGHT, MockLLM(fail_with=LLMUnavailable("x"))),
    ]
    for label, scene, client in cases:
        _, st = run(cfg, repo, banned, rules, scene=scene, client=client)
        assert st.count == 1, f"{label} 应有 1 条审计"
        assert "provenance" in st.records[0], f"{label} 的审计缺 provenance"


def test_provenance_present_even_when_audit_write_fails(cfg, repo, banned, rules) -> None:
    """INV-ADS-012：审计写入失败时**不产生**记录（故也无 provenance）—— 语义须明确。

    本测试固化这一语义：失败即整体失败、不落半条记录。
    """
    rec, _ = run(cfg, repo, banned, rules, store=FailingAuditStore())
    assert rec.result.kind == "no_ad"
    assert rec.audit_id == ""


# ---- 缺失必须显式（不得用空字符串掩盖） ----

def test_missing_version_is_unknown_not_empty(cfg) -> None:
    """REQ-ADS-AI-002（反例）：版本缺失必须写 `unknown`，**绝不写空字符串**。

    理由：空字符串会把"缺失"伪装成"有值"，使 monitor
    `decisions_missing_version_provenance` 无法统计到它 —— 缺失就不可见了。
    """
    from dataclasses import replace

    blank = replace(cfg, llm=replace(cfg.llm, provider="", model=""))
    prov = _provenance(blank)
    assert prov["model_version"] == UNKNOWN_VERSION
    assert prov["model_version"] != ""


def test_unknown_constant_is_a_meaningful_sentinel() -> None:
    """REQ-ADS-AI-002：`unknown` 哨兵值必须是可识别的常量（供 monitor 统计）。"""
    assert UNKNOWN_VERSION == "unknown"
    assert UNKNOWN_VERSION.strip()


def test_provenance_is_json_serializable(cfg, repo, banned, rules) -> None:
    """REQ-ADS-GOV-001：审计记录须可写入 JSONL ⇒ provenance 必须可 JSON 序列化。"""
    import json

    _, st = run(cfg, repo, banned, rules)
    text = json.dumps(st.records[0], ensure_ascii=False)
    assert "provenance" in text
    assert json.loads(text)["provenance"]["model_version"]


def test_provenance_does_not_leak_into_render_output(cfg, repo, banned, rules) -> None:
    """REQ-ADS-FR-004：版本溯源属**审计用**证据，不得进入对外渲染结果。"""
    import json

    from render import to_json

    rec, _ = run(cfg, repo, banned, rules)
    out = to_json(rec.result)
    assert "provenance" not in out
    assert "model_version" not in out
    assert json.loads(out)["kind"] == "ad"


# ---- 与需求登记的同步 ----

def test_config_threshold_still_matches_confirmed_decision() -> None:
    """REQ-ADS-NFR-SAFETY-005：版本溯源记录的是阈值，故须确保阈值未被悄悄改动。"""
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert cfg["selector"]["confidence_threshold"] == 0.5
