"""广告费派生：定价 → 出价与预算（REQ-ADS-FR-012 / INV-V3-007/008）。

Implements: ADR-006 D5（演示口径：广告费 = 游戏定价的 5%，预算 = 20 次曝光）
Verifies: REQ-ADS-FR-012、REQ-ADS-ARCH-016

**5% 与 20 次只允许出现在本模块**——数据文件、脚本与 pipeline 都不得硬编码，
否则改一次口径要改三处，账本对不平还没人发现（`INV-V3-007` 的静态检查会盯着这个）。

三个边界：
  · 免费游戏 `price=0` → 出价保底 1 分（`Bid` 契约要求 `bid_cents >= 1`，否则会被静默排除）；
  · 定价缺失（`None`，全量 30 条）→ 同样按免费处理（1 分）；
  · 预算取"出价 × 20 次曝光"而不是"等于定价"：否则免费游戏预算为 0，
    且 5% 取整会漂移（$14.99 → 75 分 × 20 = 1500 > 1499）。
"""

from __future__ import annotations

#: 广告费占定价的比例（演示口径，见 ADR-006 D5）
AD_FEE_RATIO = 0.05
#: 预算等于多少次曝光
DEFAULT_IMPRESSIONS = 20


def bid_cents_from_price(price_cents: int | None) -> int:
    """出价（分）= 定价 × 5%，四舍五入到分；免费/缺失保底 1 分。"""
    if price_cents is None or price_cents <= 0:
        return 1
    return max(1, round(price_cents * AD_FEE_RATIO))


def budget_cents_for(bid_cents: int, impressions: int = DEFAULT_IMPRESSIONS) -> int:
    """预算（分）= 出价 × 曝光次数，保证"第 21 次一定买不起"。"""
    if type(bid_cents) is not int or bid_cents <= 0:
        raise ValueError(f"bid_cents 必须是正整数，实际为 {bid_cents!r}")
    if type(impressions) is not int or impressions <= 0:
        raise ValueError(f"impressions 必须是正整数，实际为 {impressions!r}")
    return bid_cents * impressions
