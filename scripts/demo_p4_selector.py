"""selector 行为演示（只读，可复跑）。

用途：直观展示 P4 selector 做什么、以及在哪些情形下**拒绝**。
运行：.venv\\Scripts\\python.exe scripts\\demo_p4_selector.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ads.banned_words import BannedWords  # noqa: E402
from ads.repository import AdRepository  # noqa: E402
from selector import (  # noqa: E402
    CandidateBrief,
    ContextAssembler,
    MockLLM,
    generate_explanation,
    parse_llm_output,
    verify_explanation,
)
from selector.parser import LLMOutputError  # noqa: E402


def line(title: str) -> None:
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    repo = AdRepository.load(ROOT / "data" / "ads.json")
    banned = BannedWords.load(ROOT / "data" / "banned_words.json")

    # ---- 场景：夜间 / 手机 / 学生 → 先经预筛得到候选集 ----
    scene = {"time_slot": "night", "device": "mobile", "user_tags": ["student"]}

    from scene.models import Scene

    s = Scene(scene["time_slot"], scene["device"], tuple(scene["user_tags"]))
    cands = repo.filter_by_scene(s)
    briefs = [CandidateBrief(a.ad_id, a.title, a.category, tuple(a.target_tags)) for a in cands]

    line("① 输入：场景特征 + 规则预筛后的候选集")
    print(f"场景      : {scene}")
    print(f"候选集    : {len(briefs)} 条 -> {[b.ad_id for b in briefs]}")
    print("（注意：全部 8 个品类素材中，先被 scene_rules/素材声明筛掉了一部分）")

    # ---- ② 上下文装配：LLM 看到什么，由架构决定 ----
    ctx = ContextAssembler(budget_tokens=2000).assemble(
        f"{scene['time_slot']}/{scene['device']}/{'/'.join(scene['user_tags'])}",
        briefs,
        "请从候选列表中选择一条最适合当前场景的广告。",
    )
    line("② 上下文装配：六层 + 五步管线（LLM 看到的就是这个）")
    print(f"六层        : {list(ctx.layers)}")
    print(f"token 估算  : {ctx.tokens} / 预算 2000")
    print(f"是否压缩    : {ctx.compacted}")
    print("装配决策记录：")
    for d in ctx.decisions:
        print(f"  · {d}")
    print()
    print("层 2（INSTRUCTIONS）的实际内容 —— 这就是「闭集」约束：")
    for ln in ctx.layers["INSTRUCTIONS"].splitlines():
        print(f"    {ln}")

    # ---- ③ LLM 选择 ----
    raw = MockLLM().select(ctx.prompt)
    line("③ LLM 原始输出（未经校验，只是一段文本）")
    print(f"  {raw}")

    # ---- ④ 严格解析：闭集的执行点 ----
    judgment = parse_llm_output(raw, [b.ad_id for b in briefs])
    line("④ 严格解析 -> OutputJudgment（此刻已保证在候选集内）")
    print(f"  ad_id      = {judgment.ad_id}")
    print(f"  confidence = {judgment.confidence}")
    print(f"  reason     = {judgment.reason}")

    # ---- ⑤ 解释路径（只读，不影响决策） ----
    exp = generate_explanation(judgment, briefs)
    verdict = verify_explanation(exp, banned)
    line("⑤ 解释路径：口径 =「为什么选这条广告」")
    print(f"  解释文本 : {exp.text}")
    print(f"  校验结论 : verdict={verdict.verdict} / reason_code={verdict.reason_code}")
    print("  注意     : ExplanationVerdict 不含 ad_id 字段——结构上无法改写决策")

    # ---- ⑥ 反例：五种必须被拒的输入 ----
    line("⑥ 反例：这些都必须被拒绝（fail-closed）")
    cases: list[tuple[str, str]] = [
        ("候选集外的 ad_id", json.dumps({"ad_id": "ad_999", "reason": "r", "confidence": 0.9})),
        ("畸形 JSON", "我选 ad_001，因为它不错"),
        ("缺字段", json.dumps({"ad_id": "ad_001", "reason": "r"})),
        ("多余字段（LLM 想注入控制字段）", json.dumps({"ad_id": "ad_001", "reason": "r", "confidence": 0.9, "override": True})),
        ("confidence 越界", json.dumps({"ad_id": "ad_001", "reason": "r", "confidence": 1.5})),
        ("confidence 是 bool（Python 陷阱）", json.dumps({"ad_id": "ad_001", "reason": "r", "confidence": True})),
    ]
    ids = [b.ad_id for b in briefs]
    for label, bad_raw in cases:
        try:
            parse_llm_output(bad_raw, ids)
            print(f"  ✗ {label:34s} -> 竟然通过了！（不应发生）")
        except LLMOutputError as e:
            msg = str(e).split(": ", 1)[-1]
            print(f"  ✓ {label:34s} -> 已拒绝：{msg}")

    # ---- ⑦ 反例：解释含违禁词 ----
    line("⑦ 反例：解释含违禁词 -> 只剥离解释，决策不变")
    from selector import Explanation

    dirty = Explanation(ad_id=judgment.ad_id, text="这款产品包治百病，所以选它。", degraded=False)
    v2 = verify_explanation(dirty, banned)
    print(f"  原解释   : {dirty.text}")
    print(f"  剥离后   : {v2.text}")
    print(f"  reason   : {v2.reason_code}")
    print(f"  决策 ad_id: {judgment.ad_id}  <- 未受影响（解释路径无法触碰它）")

    # ---- ⑧ 压缩后重注入 ----
    line("⑧ 关键安全行为：上下文压缩后，约束仍在（INV-ADS-014）")
    many = [CandidateBrief(f"ad_{i:03d}", f"标题{i}", "retail", ("student",)) for i in range(1, 120)]
    big = ContextAssembler(budget_tokens=2000).assemble("night/mobile/student", many, "选一条")
    marker = "约束（不可协商）："
    print(f"  候选 119 条 -> 估算超阈值 -> 压缩：{big.compacted}")
    print(f"  压缩后 token: {big.tokens}")
    print(f"  约束仍在 prompt 中？{'是' if marker in big.prompt else '否（不变量违例！）'}")
    print("  相关决策记录：")
    for d in big.decisions:
        print(f"    · {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
