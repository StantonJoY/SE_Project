"""P1 ads 素材库模块手动验证入口。

运行（仓库根目录）：
    .\\.venv\\Scripts\\python.exe scripts\\demo_p1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from scene.models import Scene

DATA = ROOT / "data"


def main() -> None:
    repo = AdRepository.load(DATA / "ads.json")
    banned = BannedWords.load(DATA / "banned_words.json")

    print(f"素材库加载：{repo.count} 条（REQ-001/002 校验通过）")
    ad = repo.get("ad_001")
    print(f"查询示例：ad_001 = {ad.title}（品类 {ad.category}）")

    scenes = [
        ("夜间·手机·学生", Scene("night", "mobile", ("student",))),
        ("午后·平板·上班族", Scene("afternoon", "tablet", ("office_worker",))),
        ("上午·手机·学生", Scene("morning", "mobile", ("student",))),
    ]
    print("\n场景预筛（规则预筛，REQ-009 数据来源）：")
    for label, scene in scenes:
        ids = [a.ad_id for a in repo.filter_by_scene(scene)]
        print(f"  [{label}] 候选 {len(ids)} 条 -> {ids}")

    print("\n违禁词检查（REQ-008）：")
    for text in ["加班夜，一杯热美式送到家", "兼职刷单日赚500，稳赚不赔", "这款药包治百病"]:
        hit = banned.check(text)
        print(f"  {text!r} -> {hit if hit else '未命中'}")


if __name__ == "__main__":
    main()
