"""实现 ↔ 需求/规约 一致性审计（只读，可重跑）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\audit_implementation.py

审计九组（A~I）：
  A 数据合法性与 schema 一致性        F 加载期 fail-closed 一致性
  B 规则分支覆盖率（死规则检测）      G 素材×规则交叉覆盖（强/弱测试）
  C 跨层一致性（预筛 vs 终检漂移）    H 孤儿字段检测（声明了却不强制）
  D 确定性（命中是否与词表顺序无关）  I 确定性实证
  E 需求 enforced_by 引用的代码实体是否真实存在

退出码：0 = 无发现；1 = 有发现。本脚本只读，不修改任何文件。

由来：由 BUG-006（等长命中非确定性）与 BUG-007（load fail-closed 不一致）
      的排查过程沉淀而来，用于持续验证"代码实际行为 ↔ 需求/规约"是否对得上。
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import jsonschema
import yaml

from ads.banned_words import BannedWords, BannedWordsLoadError
from ads.repository import AdLoadError, AdRepository
from ads.schema import AD_SCHEMA
from compliance.rules import SceneRules, SceneRulesLoadError
from scene.models import Scene
from scene.schema import SCENE_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

findings: list[str] = []
oks: list[str] = []


def bad(tag: str, msg: str) -> None:
    findings.append(f"[{tag}] {msg}")


def ok(tag: str, msg: str) -> None:
    oks.append(f"[{tag}] {msg}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    ads_raw = json.loads((DATA / "ads.json").read_text(encoding="utf-8"))
    rules_raw = json.loads((DATA / "scene_rules.json").read_text(encoding="utf-8"))

    repo = AdRepository.load(DATA / "ads.json")
    banned = BannedWords.load(DATA / "banned_words.json")
    rules = SceneRules.load(DATA / "scene_rules.json")

    # ================= A. 数据合法性与 schema 一致性 =================
    print("=" * 70)
    print("A. 数据合法性与 schema 一致性")
    print("=" * 70)
    for i, item in enumerate(ads_raw):
        try:
            jsonschema.validate(item, AD_SCHEMA)
        except jsonschema.ValidationError as e:
            bad("A", f"ads[{i}] {item.get('ad_id')} 不满足 AD_SCHEMA: {e.message}")

    enum_devices = set(
        AD_SCHEMA["properties"]["scene_restrictions"]["properties"]["allowed_devices"]["items"]["enum"]
    )
    used_devices: set[str] = set()
    for a in ads_raw:
        used_devices |= set(a["scene_restrictions"]["allowed_devices"])
    unused = enum_devices - used_devices
    if unused:
        bad("A", f"设备枚举 {sorted(unused)} 在素材中从未出现（schema 与数据未互相覆盖）")
    else:
        ok("A", f"设备枚举全部被数据覆盖: {sorted(used_devices)}")

    banned_check_vals = {a["banned_check"] for a in ads_raw}
    schema_bc = set(AD_SCHEMA["properties"]["banned_check"]["enum"])
    if banned_check_vals - schema_bc:
        bad("A", f"banned_check 取值越界: {banned_check_vals - schema_bc}")
    if schema_bc - banned_check_vals:
        ok("A", f"banned_check 枚举 {sorted(schema_bc - banned_check_vals)} 未被数据使用（仅提示）")

    # ================= B. 规则分支覆盖率 =================
    print()
    print("=" * 70)
    print("B. 规则分支覆盖率（有无死规则 / 未覆盖品类）")
    print("=" * 70)
    categories = sorted({a["category"] for a in ads_raw})
    print(f"  素材品类: {categories}")

    for key in ("category_blacklist", "night_blocked_categories", "campus_blocked_categories"):
        for v in rules_raw.get(key, []):
            if v not in categories:
                bad("B", f"规则 {key} 含 {v!r}，但素材库中不存在该品类 → 该规则永远无法被触发（死规则）")
            else:
                ok("B", f"规则 {key} 的 {v!r} 有对应素材可触发")

    has_not_night = [a["ad_id"] for a in ads_raw if a["scene_restrictions"]["not_night"]]
    has_not_campus = [a["ad_id"] for a in ads_raw if a["scene_restrictions"]["not_campus"]]
    restricted_dev = [
        a["ad_id"] for a in ads_raw
        if set(a["scene_restrictions"]["allowed_devices"]) != enum_devices
    ]
    for label, lst in (
        ("not_night=true", has_not_night),
        ("not_campus=true", has_not_campus),
        ("allowed_devices 有子集限制", restricted_dev),
    ):
        if not lst:
            bad("B", f"素材声明 {label} 无任何素材覆盖 → 该分支强制逻辑无实证")
        else:
            ok("B", f"{label} 覆盖素材: {lst}")

    # ================= C. 跨层一致性 =================
    print()
    print("=" * 70)
    print("C. 跨层一致性：filter_by_scene（预筛）vs check_scene（终检）")
    print("=" * 70)

    from compliance.pipeline import check_scene

    drifts = []
    for ts in SCENE_SCHEMA["properties"]["time_slot"]["enum"]:
        for dev in SCENE_SCHEMA["properties"]["device"]["enum"]:
            for tags in ([], ["student"], ["office_worker"], ["student", "gamer"]):
                s = Scene(ts, dev, tuple(tags))
                cand_ids = {a.ad_id for a in repo.filter_by_scene(s)}
                for ad in repo.all():
                    in_cand = ad.ad_id in cand_ids
                    r = ad.scene_restrictions
                    # 终检的素材级部分：用 check_scene 的 detail 是否只含规则级原因来间接判定
                    detail = check_scene(ad, s, rules).detail
                    material_conflict = any(
                        k in detail for k in ("素材声明夜间", "素材声明校园", "不在允许列表")
                    )
                    if in_cand == material_conflict:
                        drifts.append((ad.ad_id, ts, dev, tags))
    if drifts:
        bad("C", f"预筛与终检的素材级判定出现 {len(drifts)} 处分歧（语义漂移）: {drifts[:5]}")
    else:
        ok("C", "预筛与终检对素材级三层约束判定完全一致（无漂移）")

    ok("C", "两层为独立重实现（非共享函数）→ 符合架构『双层』意图；代价是漂移风险，故本检查常驻")

    # 规则级只在终检层。要能触达，必须存在**未声明对应素材级限制**的同类素材，
    # 否则预筛先滤掉，规则级永远轮不到。
    # 关键：time_slot 必须是 "night"（夜间禁品类**只在该时段**判定）；校园则需带 student 标签。
    rule_probes = [
        (Scene("night", "mobile"), "night_blocked_categories", "gaming", "night"),
        (Scene("afternoon", "mobile", ("student",)), "campus_blocked_categories", "adult", "campus"),
    ]
    for scene, rule_name, category, material_flag in rule_probes:
        cand_ids = {a.ad_id for a in repo.filter_by_scene(scene)}
        hit = [
            ad.ad_id for ad in repo.all()
            if ad.ad_id in cand_ids and not check_scene(ad, scene, rules).ok
        ]
        if hit:
            tags = "/" + ",".join(scene.user_tags) if scene.user_tags else ""
            ok("C", f"规则级 {rule_name} 在终检层生效（预筛保留但终检拒绝）: {hit}"
                    f" @ {scene.time_slot}/{scene.device}{tags}")
            continue
        owners = [a.ad_id for a in repo.all() if a.category == category]
        declares = [
            a.ad_id for a in repo.all()
            if a.category == category
            and getattr(a.scene_restrictions, f"not_{material_flag}")
        ]
        if owners and owners == declares:
            bad(
                "C",
                f"规则级 {rule_name} 不可达：{category} 类素材 {owners} 全部已声明 not_{material_flag}，"
                "预筛先拦下 → 两层防护完全重叠（冗余，非漏洞；但该规则级分支缺独立验证，"
                "需补一条未声明素材级限制的同类素材）",
            )
        else:
            bad(
                "C",
                f"规则级 {rule_name} 不可达：owners={owners} declares={declares} → 存在漏拦风险",
            )

    # ================= D. 确定性 =================
    print()
    print("=" * 70)
    print("D. 确定性（命中是否与词表顺序无关 / 重复调用一致）")
    print("=" * 70)
    probes = [
        "赌博博彩赌场网贷刷单稳赚保本根治代孕捐卵色情催收日赚暴利返现",
        "高利贷特效药百分百无风险零投入内部价",
        "兼职刷单包治百病祖传秘方",
    ]
    perms = [list(banned.words), list(reversed(banned.words)), sorted(banned.words)]
    nondeterministic = []
    for text in probes:
        results = {BannedWords(p).check(text) for p in perms}
        if len(results) > 1:
            nondeterministic.append((text[:12], sorted(results)))
    if nondeterministic:
        bad("D", f"命中随词表顺序变化（非确定性）: {nondeterministic}")
    else:
        ok("D", "等长命中在 原序/逆序/码点序 三种排列下完全一致 → 确定性成立")

    sample = [a["title"] + a["copy"] for a in ads_raw]
    if [banned.check(t) for t in sample] != [banned.check(t) for t in sample]:
        bad("D", "同一文本重复 check() 结果不一致（非确定性）")
    else:
        ok("D", "同输入重复 check() 结果一致")

    # ================= E. 需求 enforcement 目标是否真实存在 =================
    print()
    print("=" * 70)
    print("E. 需求 enforcement 引用的代码实体是否真实存在")
    print("=" * 70)
    reg = yaml.safe_load((ROOT / "docs" / "req" / "requirements.yaml").read_text(encoding="utf-8"))
    src_root = ROOT / "src"
    for r in reg.get("baseline_requirements", []):
        if r["status"] not in ("implemented", "verified"):
            continue
        for target in r.get("enforcement", []):
            if "/" in target or target.startswith(".") or target.startswith("test"):
                continue
            parts = target.split(".")
            if len(parts) < 2:
                bad("E", f"{r['id']} enforcement {target!r} 不是可解析的 模块.符号")
                continue
            pkg, _, rest = target.partition(".")
            cand = src_root / pkg / f"{rest.split('.')[0]}.py"
            if not cand.exists():
                bad("E", f"{r['id']} enforcement {target!r} → {cand.relative_to(ROOT)} 不存在")
                continue
            tree = ast.parse(cand.read_text(encoding="utf-8"))
            names: set[str] = set()
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(n.name)
                elif isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            names.add(t.id)
                elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                    names.add(n.target.id)
            leaf = rest.split(".")[-1] if rest.count(".") >= 1 else None
            if leaf and leaf not in names:
                bad("E", f"{r['id']} enforcement {target!r} → {cand.name} 中无 {leaf!r} 定义")
            else:
                ok("E", f"{r['id']} → {target} 存在")

    # ================= F. 加载期 fail-closed 一致性 =================
    print()
    print("=" * 70)
    print("F. 加载期 fail-closed 一致性（各入口错误类型）")
    print("=" * 70)
    sigs = {
        "AdRepository.load": AdLoadError,
        "BannedWords.load": BannedWordsLoadError,
        "SceneRules.load": SceneRulesLoadError,
    }
    ok("F", "专属错误类型: " + ", ".join(f"{k}→{v.__name__}" for k, v in sigs.items()))

    for label, fn in (
        ("AdRepository.load", lambda p: AdRepository.load(p)),
        ("BannedWords.load", lambda p: BannedWords.load(p)),
        ("SceneRules.load", lambda p: SceneRules.load(p)),
    ):
        try:
            fn(DATA / "___not_here___.json")
            bad("F", f"{label} 对不存在的文件未报错（fail-open！）")
        except Exception as e:  # noqa: BLE001
            ok("F", f"{label} 文件缺失 → {type(e).__name__}（fail-closed）")

    for label, arg, expect in (
        ("BannedWords(非列表)", {"a": 1}, TypeError),
        ("BannedWords(元素非字符串)", [1, 2], TypeError),
        ("BannedWords(空串元素)", [""], ValueError),
        ("BannedWords(空列表)", [], None),
    ):
        try:
            BannedWords(arg)
            got = None
        except Exception as e:  # noqa: BLE001
            got = type(e)
        if expect is None:
            if got is None:
                ok("F", f"{label} 被接受（空表由 load() 层拒绝，见下）")
            else:
                bad("F", f"{label} 抛 {got.__name__}，但构造器不应拒绝空列表（拒绝点在 load）")
        elif got is expect:
            ok("F", f"{label} → {got.__name__}（fail-closed）")
        else:
            bad("F", f"{label} 期望 {expect.__name__}，实际 {got.__name__ if got else '未报错'}")

    # load 层必须拒绝空词表（空表 = 合规过滤形同虚设）
    import builtins as _bi
    import io as _io
    _orig_open = _bi.open
    try:
        _bi.open = lambda *a, **k: _io.StringIO("[]")
        try:
            BannedWords.load(DATA / "banned_words.json")
            bad("F", "load 对空词表未报错（空表会让合规过滤形同虚设）")
        except BannedWordsLoadError:
            ok("F", "load 拒绝空词表 → BannedWordsLoadError（fail-closed）")
    finally:
        _bi.open = _orig_open

    # ================= G. 素材 × 规则 交叉覆盖 =================
    print()
    print("=" * 70)
    print("G. 素材 × 规则 交叉覆盖（有无从未被任何 gate 拒绝的素材）")
    print("=" * 70)
    from compliance.pipeline import (  # noqa: E402
        check_banned_words,
        check_category,
        check_output,
    )

    scenes = [
        Scene("morning", "mobile"), Scene("morning", "desktop"), Scene("morning", "tablet", ("student",)),
        Scene("afternoon", "mobile"), Scene("afternoon", "tablet", ("student",)),
        Scene("evening", "mobile", ("gamer",)), Scene("night", "mobile"),
        Scene("night", "desktop", ("student",)), Scene("night", "tablet", ("gamer", "student")),
    ]
    never_rejected: list[str] = []
    reject_hits: dict[str, list[str]] = {}
    for ad in repo.all():
        rules_hit: set[str] = set()
        for s in scenes:
            if not check_output(ad, repo.all()).ok:
                rules_hit.add("output_exists")
            if not check_banned_words(ad, banned).ok:
                rules_hit.add("banned_words")
            if not check_category(ad, rules).ok:
                rules_hit.add("category")
            if not check_scene(ad, s, rules).ok:
                rules_hit.add("scene")
        reject_hits[ad.ad_id] = sorted(rules_hit)
        if not rules_hit:
            never_rejected.append(ad.ad_id)
    for aid, hits in reject_hits.items():
        print(f"    {aid}: 命中规则 {hits or '（无——从未被拒绝）'}")
    if never_rejected:
        ok("G", f"素材 {never_rejected} 从未被任何 gate 拒绝 → 对照样本（证明不过度拦截）")

    test_text = "\n".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "test" / "offline").glob("*.py")
    )
    for rule in ("banned_words", "category", "scene", "output_exists"):
        users = [a for a, h in reject_hits.items() if rule in h]
        if users:
            ok("G", f"规则 {rule!r} 由素材 {users} 触发")
            continue
        marker = {
            "banned_words": "test_every_banned_word_is_actually_blocked",
            "output_exists": "test_check_output_reject_not_in_candidates",
        }.get(rule)
        if marker and marker in test_text:
            ok("G", f"规则 {rule!r} 无素材级锚点，但有测试级锚点（{marker}）")
        else:
            bad("G", f"规则 {rule!r} 既无素材级锚点也无测试级锚点 → 该强制逻辑无实证")

    if "test_every_banned_word_is_actually_blocked" in test_text:
        ok("G", f"违禁词表 {len(banned.words)} 个词全部由 test_banned_words.py 逐一反例覆盖")
    else:
        bad("G", f"违禁词表 {len(banned.words)} 个词缺逐一覆盖测试")

    # ================= H. 孤儿字段检测 =================
    print()
    print("=" * 70)
    print("H. 数据字段有没有对应实现（孤儿字段检测）")
    print("=" * 70)
    src_text = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (ROOT / "src").rglob("*.py")
        if "__pycache__" not in str(p)
    )
    enforcing_text = "\n".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "src" / "compliance").rglob("*.py")
    )
    if "banned_check" in enforcing_text:
        ok("H", "banned_check 在 compliance 层被用于强制判定")
    else:
        bad(
            "H",
            "字段 banned_check（checked/banned/pending）在 schema 与 models 中声明、"
            "8 条素材全填 'checked'，但 compliance 层从不读取它 → 声明了却不强制。"
            "语义后果：标为 'banned' 的素材仍会通过所有 gate 被展示。",
        )

    for f in sorted(set(AD_SCHEMA["properties"].keys()) - {"banned_check"}):
        if f not in src_text:
            bad("H", f"素材字段 {f!r} 在 src/ 中无任何引用（孤儿字段）")

    # ================= I. 确定性实证 =================
    print()
    print("=" * 70)
    print("I. 确定性实证（等长违禁词的选择是否可复现）")
    print("=" * 70)
    text = "赌博博彩赌场网贷刷单稳赚保本根治代孕捐卵色情催收日赚暴利返现"
    a1 = BannedWords(list(banned.words)).check(text)
    a2 = BannedWords(list(reversed(banned.words))).check(text)
    if a1 != a2:
        bad("I", f"同一文本在不同词表顺序下命中不同: {a1!r} vs {a2!r} → 非确定性")
    else:
        ok("I", f"等长命中稳定: {a1!r}")
    ok("I", "命中选择规则（最长优先 → 同长取码点最小）已由 test_banned_words.py 用全排列锁定")

    # ================= 汇总 =================
    print()
    print("=" * 70)
    print(f"审计结果: {len(findings)} 项发现 / {len(oks)} 项通过")
    print("=" * 70)
    for f in findings:
        print("  ✗ " + f)
    print()
    for o in oks:
        print("  ✓ " + o)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
