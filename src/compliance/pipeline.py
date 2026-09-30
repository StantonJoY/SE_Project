"""确定性合规过滤管道（REQ-006~009）。

纯函数：不依赖外部状态、不调用 LLM、同输入同输出。
管道顺序固定：output 存在性 → 违禁词 → 品类禁忌 → 场景约束。
任一失败 → REJECT；全部通过 → APPROVE（REQ-006 零逃逸）。
"""

from __future__ import annotations

from ads.banned_words import BannedWords
from ads.models import Ad

from .models import CheckResult, ComplianceVerdict
from .rules import SceneRules


def check_output(ad: Ad, candidates: list[Ad]) -> CheckResult:
    """REQ-004/005：LLM 选择的 ad_id 必须存在于候选集。"""
    ids = {c.ad_id for c in candidates}
    ok = ad.ad_id in ids
    return CheckResult(
        ok=ok,
        rule="output_exists",
        detail="" if ok else f"ad_id {ad.ad_id!r} 不在候选集",
    )


def check_banned_words(ad: Ad, banned_words: BannedWords) -> CheckResult:
    """REQ-008：含违禁词的广告禁止展示（对 title + copy 全量检查）。"""
    hit = banned_words.check_all(ad.title, ad.copy)
    return CheckResult(
        ok=hit is None,
        rule="banned_words",
        detail="" if hit is None else f"命中违禁词 {hit!r}",
    )


def check_category(ad: Ad, rules: SceneRules) -> CheckResult:
    """REQ-007：敏感品类禁止展示。"""
    ok = ad.category not in rules.category_blacklist
    return CheckResult(
        ok=ok,
        rule="category",
        detail="" if ok else f"品类 {ad.category!r} 在黑名单",
    )


def check_scene(ad: Ad, scene, rules: SceneRules) -> CheckResult:
    """REQ-009：广告不得违反场景硬约束。

    两层检查：
      1. 素材自身声明（not_night / not_campus / allowed_devices）
      2. 规则级（night_blocked_categories / campus_blocked_categories）

    scene 使用 duck-typing：须有 time_slot / device / user_tags。
    校园信号 = user_tags 包含 "student"。
    """
    r = ad.scene_restrictions
    problems: list[str] = []

    # 素材自身声明
    if r.not_night and scene.time_slot == "night":
        problems.append("素材声明夜间不展示")
    is_campus = "student" in (scene.user_tags or [])
    if r.not_campus and is_campus:
        problems.append("素材声明校园场景不展示")
    if r.allowed_devices and scene.device not in r.allowed_devices:
        problems.append(f"设备 {scene.device!r} 不在允许列表 {list(r.allowed_devices)}")

    # 规则级
    if scene.time_slot == "night" and ad.category in rules.night_blocked_categories:
        problems.append(f"品类 {ad.category!r} 夜间禁展示")
    if is_campus and ad.category in rules.campus_blocked_categories:
        problems.append(f"品类 {ad.category!r} 校园禁展示")

    return CheckResult(
        ok=not problems,
        rule="scene",
        detail="；".join(problems),
    )


def run_compliance(
    ad: Ad,
    scene,
    candidates: list[Ad],
    banned_words: BannedWords,
    rules: SceneRules,
) -> ComplianceVerdict:
    """合规管道（REQ-006）：任一检查失败 → REJECT。

    顺序：output_exists → banned_words → category → scene。
    """
    results = (
        check_output(ad, candidates),
        check_banned_words(ad, banned_words),
        check_category(ad, rules),
        check_scene(ad, scene, rules),
    )
    return ComplianceVerdict(approved=all(r.ok for r in results), results=results)
