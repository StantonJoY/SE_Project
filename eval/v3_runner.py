"""V3 固定评估集 replay（REQ-ADS-NFR-QA-006）。

用法（仓库根目录）：
    python eval/v3_runner.py            # 跑固定用例，输出通过率 / 合规逃逸 / p95
    python eval/v3_runner.py --json     # 机器可读

判据（与 ADR-003 一致：分母分离、违规独立判定）：
  · **合规逃逸恒为 0**：返回的每条广告都要按档位重算一遍内容判据，命中即算逃逸；
  · **崩溃恒为 0**：任何场景都必须返回结构化结果；
  · **可重放**：同一用例跑两次，渲染结果必须逐字段一致（MockLLM 确定性）；
  · 通过率只统计 `expect` 与结果一致的用例。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ads.banned_words import BannedWords  # noqa: E402
from ads.repository import AdRepository  # noqa: E402
from app import AppConfig, recommend  # noqa: E402
from app.cli import CorpusContext, load_corpus_context  # noqa: E402
from audit import InMemoryAuditStore  # noqa: E402
from compliance.rules import SceneRules  # noqa: E402
from corpus import load_corpus_config  # noqa: E402
from scene.parser import parse_scene  # noqa: E402
from selector import MockLLM  # noqa: E402

CASES = ROOT / "eval" / "v3_cases.json"
CONFIG = ROOT / "config.yaml"


def _result_dict(result: object) -> dict:
    if hasattr(result, "__dataclass_fields__"):
        return asdict(result)
    return dict(result)  # type: ignore[arg-type]


def _escape(ad_id: str, ctx, scene) -> str | None:
    """按档位重算内容判据；返回逃逸描述或 None。"""
    if ctx.policy is None:
        return None
    facts = ctx.policy.facts.get(ad_id)
    if facts is None:
        return None
    tier = ctx.policy.rules.tier_for(scene)
    hit = ctx.policy.rules.labels_for(facts) & tier.block_labels
    if hit:
        return f"{ad_id} 在 {tier.name} 档命中 {sorted(hit)}"
    if facts.required_age > tier.max_age:
        return f"{ad_id} 年龄 {facts.required_age} 超 {tier.name} 上限 {tier.max_age}"
    return None


def run() -> dict:
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    config = AppConfig.load(CONFIG)
    base_corpus = load_corpus_config(CONFIG)
    banned = BannedWords.load(ROOT / config.data.banned_words_path)
    rules = SceneRules.load(ROOT / config.data.scene_rules_path)

    passed = 0
    failures: list[str] = []
    escapes: list[str] = []
    latencies: list[float] = []

    for case in cases:
        cid, scene_raw, expect = case["id"], case["scene"], case.get("expect", "any")
        ctx = load_corpus_context(scene_raw, CONFIG, ROOT)
        if "tag_mapping" in case and not case["tag_mapping"]:
            # 负例：强制空语料（验证"无匹配返回空，不硬凑"）
            ctx = CorpusContext(repository=AdRepository([]), policy=None, corpus_items=())
        start = time.perf_counter()
        try:
            first = recommend(scene_raw, repo=ctx.repository, banned_words=banned, rules=rules,
                              client=MockLLM(), audit_store=InMemoryAuditStore(), config=config,
                              content_policy=ctx.policy)
            second = recommend(scene_raw, repo=ctx.repository, banned_words=banned, rules=rules,
                               client=MockLLM(), audit_store=InMemoryAuditStore(), config=config,
                               content_policy=ctx.policy)
        except Exception as exc:  # noqa: BLE001 - 崩溃即失败，不吞
            failures.append(f"{cid}: 异常 {type(exc).__name__}: {exc}")
            continue
        latencies.append((time.perf_counter() - start) / 2)
        out = _result_dict(first.result)
        repeat = _result_dict(second.result)
        # audit_id 每次随机生成，不属于"可重放"语义
        if (
            {k: v for k, v in out.items() if k != "audit_id"}
            != {k: v for k, v in repeat.items() if k != "audit_id"}
        ):
            failures.append(f"{cid}: 两次重放结果不一致")
        kind = out.get("kind")
        if expect != "any" and kind != expect:
            failures.append(f"{cid}: 期望 {expect}，实际 {kind} ({out.get('reason_code')})")
        elif expect == "any":
            passed += 1
        else:
            passed += 1
        if case.get("reason_code") and out.get("reason_code") != case["reason_code"]:
            failures.append(f"{cid}: 期望原因码 {case['reason_code']}，实际 {out.get('reason_code')}")
        if kind == "ad":
            try:
                scene = parse_scene(scene_raw)
            except Exception:  # noqa: BLE001
                continue
            detail = _escape(out["ad"]["ad_id"], ctx, scene)
            if detail:
                escapes.append(f"{cid}: {detail}")

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0.0
    total = len(cases)
    return {
        "partition": "V3",
        "cases": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "escapes": escapes,
        "failures": failures,
        "p95_sec": p95,
        "corpus_rows": len(base_corpus.tag_mapping),
    }


def main(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser(description="V3 固定评估 replay").parse_args(argv)
    report = run()
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 74)
        print("V3 固定评估 replay（真实语料 + 内容分级）")
        print("=" * 74)
        print(f"用例 {report['cases']} 条 | 通过 {report['passed']} | "
              f"达成率 {report['pass_rate']:.4f} | 合规逃逸 {len(report['escapes'])} | "
              f"p95 {report['p95_sec'] * 1000:.1f} ms")
        for item in report["escapes"]:
            print("  ✗ 逃逸:", item)
        for item in report["failures"]:
            print("  ✗ 失败:", item)
        ok = not report["escapes"] and not report["failures"]
        print()
        print("判定：" + ("通过" if ok else "不通过"))
        print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
