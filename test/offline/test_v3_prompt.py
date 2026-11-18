"""V3 提示词语义对齐的回归测试（ADR-006 D9 / REQ-ADS-AI-001）。

Verifies: REQ-ADS-AI-001（解释与建议的隔离）、REQ-ADS-NFR-SAFETY-005（建议层不得替代合规）

本模块锁定三件事，防止以后被误删：
  ① 场景摘要必须带语义（否则模型不知道 family/student 是什么）；
  ② 约束里必须禁止使用「对作品的外部知识」（防先验污染）；
  ③ HISTORY 层不得再带内部文档路径（对模型无意义，纯占预算）。
另测：V2 相关性提示词必须定义 relevance = 与场景标签的匹配度。
"""

from __future__ import annotations

from pathlib import Path

from selector import CandidateBrief, ContextAssembler, format_scene_summary
from selector import relevance as rel

ROOT = Path(__file__).resolve().parents[2]


def _scene_raw(tag: str) -> dict:
    return {"time_slot": "afternoon", "device": "desktop", "user_tags": [tag]}


def test_scene_summary_carries_semantics():
    """REQ-ADS-AI-001：场景摘要必须把枚举翻译成人类/模型可理解的含义。"""

    class Scene:
        time_slot = "afternoon"
        device = "desktop"
        user_tags = ["family"]

    summary = format_scene_summary(Scene())
    assert "afternoon" in summary and "下午" in summary
    assert "desktop" in summary and "桌面" in summary
    assert "family" in summary and "家庭场景" in summary


def test_prompt_contains_scene_semantics_and_no_external_knowledge():
    """REQ-ADS-AI-001：渲染后的 prompt 必须含场景语义与「不得使用外部知识」约束。"""

    class Scene:
        time_slot = "night"
        device = "mobile"
        user_tags = ["student"]

    briefs = [CandidateBrief("ad_1", "Some Game", "RPG", ("Fantasy", "Relaxing"))]
    assembled = ContextAssembler(budget_tokens=2000).assemble(
        format_scene_summary(Scene()), briefs, "请选出与场景最匹配的一条。"
    )
    prompt = assembled.prompt
    assert "校园场景" in prompt, "学生标签必须解释成校园场景语义"
    assert "不得使用你对这些作品的外部知识" in prompt
    assert "候选条目" in prompt, "不得再称候选为「广告」（素材是游戏条目）"


def test_history_layer_has_no_internal_doc_path():
    """REQ-ADS-AI-001：HISTORY 层不得把仓库内部文档路径塞给模型。"""

    class Scene:
        time_slot = "night"
        device = "mobile"
        user_tags = []

    assembled = ContextAssembler(budget_tokens=2000).assemble(
        format_scene_summary(Scene()), [CandidateBrief("ad_1", "T", "C", ())], "选一条。"
    )
    assert "docs/architecture" not in assembled.prompt
    assert "不适用" in assembled.prompt


def test_relevance_prompt_defines_relevance_semantics():
    """REQ-ADS-AI-001：V2 相关性提示词必须定义 relevance = 与场景标签的匹配度。"""
    text = rel.RELEVANCE_STANDING_CONSTRAINTS
    assert "matches the stated scene tags" in text
    assert "NOT how famous" in text
    assert rel.RELEVANCE_PROMPT_VERSION == "relevance-v2.2"
