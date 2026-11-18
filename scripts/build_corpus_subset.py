#!/usr/bin/env python3
"""从全量 Steam 语料生成**确定性**入库子集（REQ-ADS-FR-013 / ADR-006 D7）。

用法：
    python scripts/build_corpus_subset.py \
        --items <全量 items.jsonl> --tags <全量 tags.jsonl> \
        --out-dir data/corpus --n 5000

规则（无随机数，双跑逐字节一致）：
  ① 必含：`--demo-items` 指定的条目（默认取 out-dir 中现有子集的 item_id，保持测试可复现）
  ② 必含：`genres` 为空的全部条目（实测 34/25899，随机抽样会漏掉大半）
  ③ 必含：`required_age >= 13` 的全部条目（年龄兜底判据的样本）
  ④ 配额：每个 `content_descriptors` 组合各取 N 条（内容并集判据的样本）
  ⑤ 配额：免费游戏 N 条（定价派生 5% 的边界）
  ⑥ 余量：按主 genre 轮转补齐，避免 Indie 一家吃掉 67%
  ⑦ 剥离 `description_clean`（43.5 MB）与无关字段，只留入选字段
  ⑧ 产出 `manifest.json`：来源、行数、规则、两份文件的 SHA-256
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ITEM_FIELDS = (
    "item_id",
    "name",
    "genres",
    "native_tags",
    "required_age",
    "content_descriptors",
    "review_count",
    "price_final",
    "is_free",
)
TAG_FIELDS = ("item_id", "summary", "tags", "model", "prompt_ver", "vocab_ver")

DESCRIPTOR_QUOTA = 200
FREE_QUOTA = 200


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_subset(
    items: list[dict], tags: dict[int, dict], n: int, demo_ids: set[int],
) -> dict[int, str]:
    """纯函数：决定选哪些 item_id 以及入选理由（无 IO、无随机数）。

    与 IO 分开，是为了让"抽样规则"本身可被测——不依赖全量数据文件。
    """
    items = sorted(items, key=lambda i: i["item_id"])
    chosen: dict[int, str] = {}

    def take(rows: list[dict], quota: int, reason: str) -> None:
        taken = 0
        for item in rows:
            if taken >= quota:
                break
            if item["item_id"] in chosen:
                continue
            chosen[item["item_id"]] = reason
            taken += 1

    # ① 现有 demo 条目（保持既有测试/需求里的 item_id 可复现）
    for item in items:
        if item["item_id"] in demo_ids:
            chosen[item["item_id"]] = "demo"

    # ② / ③ 边界样本全量纳入
    take([i for i in items if not i.get("genres")], 10**9, "empty_genres")
    take([i for i in items if i.get("required_age", 0) >= 13], 10**9, "age_gated")

    # ④ 内容标识：按组合配额
    by_combo: dict[tuple, list[dict]] = defaultdict(list)
    for item in items:
        if item.get("content_descriptors"):
            by_combo[tuple(item["content_descriptors"])].append(item)
    for combo, rows in sorted(by_combo.items()):
        take(rows, DESCRIPTOR_QUOTA, "descriptors:" + json.dumps(list(combo)))

    # ⑤ 免费游戏
    take([i for i in items if i.get("is_free")], FREE_QUOTA, "free")

    # ⑥ 按主 genre 轮转补齐
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        key = (item.get("genres") or ["<none>"])[0]
        buckets[key].append(item)
    names = sorted(buckets)
    cursor = 0
    while len(chosen) < n:
        progressed = False
        for _ in range(len(names)):
            name = names[cursor % len(names)]
            cursor += 1
            if buckets[name]:
                item = buckets[name].pop(0)
                if item["item_id"] not in chosen:
                    chosen[item["item_id"]] = "genre:" + name
                    progressed = True
                    break
        if not progressed:
            break
    return chosen


def build_subset(
    items_path: Path, tags_path: Path, out_dir: Path, n: int, demo_ids: set[int],
) -> dict:
    items = _read_jsonl(items_path)
    tags = {row["item_id"]: row for row in _read_jsonl(tags_path)}
    chosen = select_subset(items, tags, n, demo_ids)
    picked = sorted(chosen)
    by_id = {i["item_id"]: i for i in items}
    out_dir.mkdir(parents=True, exist_ok=True)
    items_out = out_dir / "items.jsonl"
    tags_out = out_dir / "tags.jsonl"
    with items_out.open("w", encoding="utf-8") as fi, tags_out.open("w", encoding="utf-8") as ft:
        for item_id in picked:
            source = by_id[item_id]
            fi.write(json.dumps({k: source.get(k) for k in ITEM_FIELDS}, ensure_ascii=False) + "\n")
            row = tags[item_id]
            ft.write(json.dumps({k: row.get(k) for k in TAG_FIELDS}, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": "1.0",
        "generator": "scripts/build_corpus_subset.py",
        "source": {
            "items_rows": len(items),
            "tags_rows": len(tags),
            "items_file_bytes": items_path.stat().st_size,
        },
        "subset": {
            "rows": len(picked),
            "items_file": "items.jsonl",
            "tags_file": "tags.jsonl",
            "items_sha256": _sha256(items_out),
            "tags_sha256": _sha256(tags_out),
        },
        "rules": {
            "deterministic": True,
            "must_include": ["demo_ids", "empty_genres(all)", "required_age>=13(all)"],
            "quotas": {
                "descriptors_per_combo": DESCRIPTOR_QUOTA,
                "free_games": FREE_QUOTA,
                "remaining": "round-robin by primary genre",
            },
            "stripped_fields": ["description_clean"],
            "kept_item_fields": list(ITEM_FIELDS),
            "kept_tag_fields": list(TAG_FIELDS),
        },
        "composition": dict(Counter(chosen.values()).most_common()),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成确定性语料子集")
    parser.add_argument("--items", required=True, help="全量 items.jsonl")
    parser.add_argument("--tags", required=True, help="全量 tags.jsonl")
    parser.add_argument("--out-dir", default="data/corpus")
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument(
        "--demo-items",
        default=None,
        help="需保留的 item_id 清单（默认 <out-dir>/demo_ids.txt；不得从待覆盖的产物反推）",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    demo_path = Path(args.demo_items) if args.demo_items else (out_dir / "demo_ids.txt")
    if not demo_path.exists():
        raise SystemExit(f"缺少 demo id 清单：{demo_path}（抽样规则需要它保持测试可复现）")
    demo_ids = {int(x) for x in demo_path.read_text(encoding="utf-8").split()}

    manifest = build_subset(Path(args.items), Path(args.tags), out_dir, args.n, demo_ids)
    print(
        f"子集 {manifest['subset']['rows']} 条 → {out_dir} "
        f"(items {manifest['subset']['items_sha256'][:12]}… / tags {manifest['subset']['tags_sha256'][:12]}…)"
    )
    print("组成:", json.dumps(manifest["composition"], ensure_ascii=False)[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
