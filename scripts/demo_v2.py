"""Executable V2 demo with fresh temporary ledgers (ADR-005).

Verifies: REQ-ADS-ARCH-005/007, REQ-ADS-FR-008, REQ-ADS-NFR-QA-003.

stdout is machine JSON; --zh adds readable Chinese commentary on stderr.
No shared ads, bids or persistent ledger files are modified.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from app.pipeline_v2 import recommend_v2
from bidding import Ledger, validate_bids
from compliance.rules import SceneRules
from render.schema_v2 import validate_v2_result
from selector.relevance import FixedRelevanceClient


def run_demo() -> dict:
    """Demonstrate observed outcomes and arithmetic using isolated SQLite databases."""
    repo = AdRepository.load(ROOT / "data/ads.json")
    banned = BannedWords.load(ROOT / "data/banned_words.json")
    rules = SceneRules.load(ROOT / "data/scene_rules.json")
    with (ROOT / "data/bids-v2.json").open(encoding="utf-8") as stream:
        bids = validate_bids(json.load(stream), known_ad_ids={ad.ad_id for ad in repo.all()})
    client = FixedRelevanceClient({"ad_001": 90, "ad_002": 50})
    # ad_002 declares not_night=true. Morning preserves the V1 material restriction.
    scene = {"time_slot": "morning", "device": "mobile", "user_tags": ["student"]}
    scenarios: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="cs5351-v2-demo-", dir=ROOT) as temp:
        db = Path(temp) / "auction.sqlite3"
        with Ledger(db) as ledger:
            ledger.seed(bids)

            def run(request_id: str) -> dict:
                result = recommend_v2(scene, request_id=request_id, repo=repo, bids=bids,
                                      client=client, ledger=ledger, banned_words=banned, rules=rules)
                assert not validate_v2_result(result), result
                return result

            first = run("normal-1")
            assert first["ad"]["ad_id"] == "ad_001" and first["auction"]["score"] == 10800
            scenarios.append({"scenario": "normal_ad_001_wins", "result": first})
            before_repeat = ledger.budgets()
            repeat = run("normal-1")
            assert repeat == first and ledger.budgets() == before_repeat and len(ledger.audit_records()) == 1
            scenarios.append({"scenario": "repeat_id_no_extra_charge", "result": repeat})
            second = run("normal-2")
            assert second["ad"]["ad_id"] == "ad_001" and ledger.budgets()["ad_001"]["remaining_cents"] == 0
            scenarios.append({"scenario": "second_spend_exhausts_ad_001", "result": second})
            third = run("normal-3")
            assert third["ad"]["ad_id"] == "ad_002"
            scenarios.append({"scenario": "next_eligible_ad_002", "result": third})
            persisted = ledger.budgets()
        with Ledger(db) as ledger:
            ledger.seed(bids)
            assert ledger.budgets() == persisted
            restarted = recommend_v2(scene, request_id="normal-3", repo=repo, bids=bids, client=client,
                                     ledger=ledger, banned_words=banned, rules=rules)
            assert restarted == third and len(ledger.audit_records()) == 3
            scenarios.append({"scenario": "restart_preserves_spend_and_replay", "result": restarted})
            main_budgets = ledger.budgets()
            main_audit_count = len(ledger.audit_records())
        medical = validate_bids([{"ad_id": "ad_009", "bid_cents": 100, "budget_cents": 200}],
                                known_ad_ids={ad.ad_id for ad in repo.all()})
        with Ledger(Path(temp) / "medical.sqlite3") as ledger:
            ledger.seed(medical)
            rejected = recommend_v2(scene, request_id="medical-1", repo=repo, bids=medical,
                                    client=FixedRelevanceClient({"ad_009": 100}), ledger=ledger,
                                    banned_words=banned, rules=rules)
            assert rejected["kind"] == "no_ad" and rejected["reason_code"] == "compliance_rejected"
            assert ledger.budgets()["ad_009"]["spent_cents"] == 0 and len(ledger.audit_records()) == 1
            scenarios.append({"scenario": "medical_compliance_reject_zero_charge", "result": rejected,
                              "observed_spent_cents": 0})

        def fail_before_audit(stage: str) -> None:
            if stage == "before_audit":
                raise OSError("demo transaction fault")

        with Ledger(Path(temp) / "fault.sqlite3", fault_hook=fail_before_audit) as ledger:
            ledger.seed(bids)
            failed = recommend_v2(scene, request_id="fault-1", repo=repo, bids=bids, client=client,
                                  ledger=ledger, banned_words=banned, rules=rules)
            spent = sum(row["spent_cents"] for row in ledger.budgets().values())
            assert failed["kind"] == "status_unknown" and spent == 0 and not ledger.audit_records()
            scenarios.append({"scenario": "transaction_fault_rolls_back_zero_observed_charge", "result": failed,
                              "observed_spent_cents": spent, "observed_audit_count": 0})
    return {"provider": "fixed_offline", "live_provider_tested": False, "scene": scene,
            "scenario_count": len(scenarios), "passed": True, "scenarios": scenarios,
            "main_budgets": main_budgets, "main_audit_count": main_audit_count,
            "total_observed_spend_cents": sum(row["spent_cents"] for row in main_budgets.values())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zh", "--chinese", action="store_true", dest="zh")
    args = parser.parse_args(argv)
    report = run_demo()
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))
    if args.zh:
        print("V2 七项演示通过：正常竞价、请求去重、预算耗尽、切换广告、重启持久化、医疗拒绝零扣费、事务故障回滚。", file=sys.stderr)
        print("使用 morning 场景以遵守 ad_002 的夜间禁投限制；固定离线相关性，不声称已调用真实模型。", file=sys.stderr)
        print(f"主账本共 {report['main_audit_count']} 条审计，实际花费 {report['total_observed_spend_cents']} 分。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
