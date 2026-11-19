#!/usr/bin/env python3
"""由语料生成 V2 竞价用的 bid sidecar（REQ-ADS-FR-012 / ARCH-016）。

用法：
    python scripts/build_bids_v3.py --corpus data/corpus/items.jsonl --out data/bids-corpus.json

产物是**可复算的派生数据**：出价与预算全部来自 `corpus.pricing`，
脚本本身不出现 5% 或 20 次（唯一的 5% 常量在 `src/corpus/pricing.py`）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from corpus.pricing import bid_cents_from_price, budget_cents_for  # noqa: E402


def build_bids(items_path: Path) -> list[dict]:
    rows: list[dict] = []
    with items_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            bid = bid_cents_from_price(item.get("price_final"))
            rows.append({
                "ad_id": f"ad_{item['item_id']}",
                "bid_cents": bid,
                "budget_cents": budget_cents_for(bid),
                "status": "active",
            })
    rows.sort(key=lambda row: int(row["ad_id"][3:]))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成语料竞价 sidecar")
    parser.add_argument("--corpus", default="data/corpus/items.jsonl")
    parser.add_argument("--out", default="data/bids-corpus.json")
    args = parser.parse_args(argv)

    rows = build_bids(Path(args.corpus))
    Path(args.out).write_text(
        json.dumps(rows, ensure_ascii=False, indent=0) + "\n", encoding="utf-8"
    )
    bids = [r["bid_cents"] for r in rows]
    print(f"{len(rows)} 条 → {args.out}；出价 min={min(bids)} max={max(bids)} "
          f"（1 分 = 免费或缺失定价）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
