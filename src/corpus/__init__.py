"""V3 真实语料接入（只读 + 投影旁路）。

Implements: ADR-006 D2/D3（语料只读、双源并存、投影不进 Ad 契约）
Verifies: REQ-ADS-FR-009、FR-010、FR-011、ARCH-013、ARCH-014、NFR-COST-002

本包是第 9 个架构元素（blueprint §4 ⑨）：
  - 只读加载 `data/corpus/{items,tags}.jsonl`，**不加载 description_clean**；
  - 把语料投影成合法 `Ad`（`ad_id = ad_<item_id>`），扩展信息走 `CorpusFacts` 旁路；
  - 候选生成是确定性纯函数（命中标签数降序 + item_id 升序）；
  - 依赖方向单向：`corpus` 只被 `app` 导入，自身不得 import `selector`/`compliance`/`audit`。
"""

from __future__ import annotations

from .config import CorpusConfig, CorpusConfigError, load_corpus_config
from .models import TAG_DIMENSIONS, CorpusFacts, CorpusItem
from .projection import corpus_to_ad, project_all
from .repository import CorpusLoadError, CorpusRepository
from .select import select_candidates

__all__ = [
    "TAG_DIMENSIONS",
    "CorpusConfig",
    "CorpusConfigError",
    "CorpusFacts",
    "CorpusItem",
    "CorpusLoadError",
    "CorpusRepository",
    "corpus_to_ad",
    "load_corpus_config",
    "project_all",
    "select_candidates",
]
