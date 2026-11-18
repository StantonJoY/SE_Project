"""V3 广告费派生与 V2 结算的离线测试（PR-3）。

Verifies: REQ-ADS-FR-012（广告费 = 定价 × 5%）、REQ-ADS-ARCH-016（派生唯一来源 + 预算不可透支）
Implements: ADR-006 D5

本模块包含多条**反例**（negative test）：免费游戏必须保底 1 分（否则会被 `Bid` 契约静默排除）、
第 21 次成交必须被拒（不得透支）、5% 常量不得散落在别处。
对应不变量：INV-V3-007（派生唯一来源）、INV-V3-008（预算不可透支）。
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from bidding import Bid, InsufficientBudget, Ledger, validate_bids
from corpus import CorpusRepository
from corpus.pricing import AD_FEE_RATIO, DEFAULT_IMPRESSIONS, budget_cents_for, bid_cents_from_price

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "data" / "corpus"


@pytest.fixture(scope="module")
def corpus():
    return CorpusRepository.load(CORPUS_DIR / "items.jsonl", CORPUS_DIR / "tags.jsonl")


@pytest.mark.parametrize(
    "price,expected",
    [
        (1499, 75),    # $14.99 → 74.95 → 四舍五入 75
        (5999, 300),   # $59.99
        (1999, 100),   # $19.99
        (999, 50),     # $9.99 → 49.95 → 50
        (499, 25),     # $4.99
        (0, 1),        # 免费 → 保底 1 分
        (None, 1),     # 定价缺失 → 同样保底
    ],
)
def test_bid_is_five_percent_of_price(price, expected):
    """REQ-ADS-FR-012：出价 = 定价 × 5%（四舍五入到分）；免费/缺失保底 1 分。"""
    assert bid_cents_from_price(price) == expected


def test_free_game_bids_one_cent(corpus):
    """REQ-ADS-FR-012 反例：免费游戏若给 0 分，会被 `Bid` 契约（bid_cents>=1）静默排除。"""
    free_items = [item for item in corpus.all() if not item.price_cents or item.is_free]
    assert free_items, "子集必须含免费/缺价条目（抽样规则保证）"
    for item in free_items[:20]:
        assert bid_cents_from_price(item.price_cents) == 1
        Bid(ad_id=f"ad_{item.item_id}", bid_cents=1, budget_cents=budget_cents_for(1))


def test_budget_equals_twenty_impressions(corpus):
    """REQ-ADS-FR-012：预算 = 出价 × 20 次曝光（配置常量）。"""
    assert DEFAULT_IMPRESSIONS == 20
    for item in corpus.all()[:50]:
        bid = bid_cents_from_price(item.price_cents)
        assert budget_cents_for(bid) == bid * 20


def test_twenty_impressions_exhaust_budget():
    """REQ-ADS-ARCH-016 / INV-V3-008：20 次成交恰耗尽，第 21 次被拒且不透支。"""
    for price in (0, 1499, 5999):          # 免费 / 中价 / 高价
        bid = bid_cents_from_price(price)
        budget = budget_cents_for(bid)
        ad_id = f"ad_{price}"
        bids = validate_bids([{"ad_id": ad_id, "bid_cents": bid, "budget_cents": budget}])
        ledger = Ledger()                   # 内存库
        try:
            ledger.seed(bids)
            for n in range(1, 21):
                result = {"kind": "ad", "request_id": f"r{n}", "audit_id": f"aud-{n}",
                          "ad": {"ad_id": ad_id}, "auction": {}}
                ledger.finalize(f"r{n}", f"r{n}", result, {"case": "pricing"}, ad_id=ad_id, charge_cents=bid)
            snapshot = ledger.budgets()[ad_id]
            assert snapshot["remaining_cents"] == 0
            assert snapshot["status"] == "exhausted"
            with pytest.raises(InsufficientBudget):
                ledger.finalize("r21", "r21",
                                {"kind": "ad", "request_id": "r21", "audit_id": "aud-21",
                                 "ad": {"ad_id": ad_id}, "auction": {}},
                                {"case": "over"}, ad_id=ad_id, charge_cents=bid)
            assert ledger.budgets()[ad_id]["spent_cents"] == budget, "第 21 次不得产生任何扣费"
        finally:
            ledger.close()


def test_five_percent_constant_single_source():
    """REQ-ADS-ARCH-016 / INV-V3-007：5% 系数只允许出现在 corpus/pricing.py。

    扫描范围是**可能计算广告费**的三处：`src/corpus`、`src/app`、`scripts`。
    `src/audit/metrics.py` 里的 0.05 是监控阈值（解析失败率 ≤5%），与费用无关，故不在范围。
    """
    offenders = []
    for base in (ROOT / "src" / "corpus", ROOT / "src" / "app", ROOT / "scripts"):
        for path in sorted(base.rglob("*.py")):
            if path.name == "pricing.py" and path.parent.name == "corpus":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, float) and node.value == 0.05:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not offenders, f"5% 常量出现在 {offenders}（应只由 corpus.pricing 提供）"
    assert AD_FEE_RATIO == 0.05


def test_bids_sidecar_matches_corpus_prices(corpus):
    """REQ-ADS-FR-012：`data/bids-corpus.json` 必须能由语料 + pricing 复算出来。"""
    rows = json.loads((ROOT / "data" / "bids-corpus.json").read_text(encoding="utf-8"))
    assert len(rows) == corpus.count
    by_id = {row["ad_id"]: row for row in rows}
    for item in corpus.all()[:200]:
        row = by_id[f"ad_{item.item_id}"]
        expected = bid_cents_from_price(item.price_cents)
        assert row["bid_cents"] == expected
        assert row["budget_cents"] == budget_cents_for(expected)
        assert row["status"] == "active"
