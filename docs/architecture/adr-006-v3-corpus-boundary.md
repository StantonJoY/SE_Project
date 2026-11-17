# ADR-006：V3 轮次接入与真实语料边界

> **状态**：`Proposed`（待具名人类批准后改 `Accepted`）
> **日期**：2026-11-17 · **决策者**：B（架构/AI）+ A（产品/流程）· **批准人**：⏳ 待填
> **覆盖的受保护路径**：`src/compliance/`、`data/`、`eval/`、`src/app/pipeline_v2.py`、
> `scripts/fitness_functions.py`、`docs/req/requirements.yaml`、`docs/code-governance/acceptance-coverage-map.yaml`

---

## 1. 背景

V1 用 14 条手写素材、V2 在其上加了竞价与原子结算。课程要求的第三轮（V3）要做**真实语料接入**：
用 Steam 游戏数据替换手写素材，让"场景化推荐"面对真实脏数据。

动工前做了一次只读 spike（30 条真实样本，见 `V3spike结论.md`），四个数字决定了本 ADR：

| 观测 | 数值 | 含义 |
|---|---|---|
| 投影能否通过现有 `AD_SCHEMA` + `AdRepository` | **30/30** | 不需要新类型 |
| 现有 V1 管道能否跑通 | 3 个场景全部出 `ad` | 不需要改编排 |
| 现有合规对真实语料的拦截 | **0/30**（其中 17 条带内容标记） | 必须扩合规，否则等于把脏内容接进生产 |
| K=30 的上下文开销 | 1152 token / 2000（58%） | K 上限由预算反推，不是随手定 |

同时确认：只看 `content_descriptors` 会漏 **7/30**（Among Us 的 descriptors 为空但 warnings 有 Blood）；
`required_age` 有 **24/30 为 0**（0 表示"无评级"而非"适合儿童"，CS2 就是 0 但有 `[2,5]`）。

---

## 2. 决策

### D1 · 轮次目录：沿用 `docs/`，不新建 `docs3/`

**理由**：验证平面（`validate_requirements.py`、`fitness_functions.py`、`check_safety_paths.py`、
`acceptance-coverage-map.yaml`）全部绑定 `docs/req/` 与 `docs/architecture/` 路径。
新建 `docs3/` 会让 V3 的 18 条需求**脱离所有自动化校验**——这比"轮次目录不整齐"危险得多。
V2 已有先例（ADR-005 放在 `docs/architecture/`，未建 `docs2/`），本轮延续并在 `evolution_rounds` 显式登记 V3。

**代价**：`docs/` 里同时存在三轮工件。缓解：所有 V3 条目带 `version: "V3"`，小节标题标 `V3 增量`。

### D2 · 语料只读、双源并存

新增 `src/corpus/`（第 9 个架构元素），**只读**加载 `data/corpus/{items,tags}.jsonl`；
14 条手写素材路径保持原样，两者并存互不覆盖。
**明确不加载 `description_clean`**（样本最长 8,007 字符、全量最长 63,404）：它是 BM25/embedding 的输入，
本轮的候选生成是标签匹配，不需要长文本；不加载也让"进 prompt 的内容"可审计。

### D3 · 投影旁路：`Ad` 复用，扩展信息不入 Ad

`corpus_to_ad(item)` 产出**合法的 `Ad`**（`ad_id = "ad_" + item_id`，满足 `^ad_[0-9]+$`），
内容标识 / warnings / 年龄 / 七维标签放在并行的 `CorpusFacts` 映射里。
`AD_SCHEMA` **一个字都不改**，`AdRepository` 行为**零改动**。

> spike 已经证明 30/30 可以过——草案原先"投影不过 AdRepository"的说法是错的。

### D4 · 合规扩展：只动两个函数，五步顺序不变

`run_compliance(..., facts=None)` 与 `check_scene(..., facts=None)` 各加一个**可选**参数；
不传 `facts` 时行为与 V1 完全一致（旧测试全绿即为证据）。
规则只作为既有步骤内部的扩充：`output_exists → banned_words → banned_check → category → scene` **逐位不变**。

判据分两层：
1. **主判据**：`content_warnings ∪ 映射后的 content_descriptors` 与场景禁项求交；
2. **兜底判据**：`required_age` 超场景上限。

**为什么不放在 corpus 侧过滤**：那会让"compliance 是唯一权威"出现裂缝；本项目的安全主张依赖这一条。

### D5 · 定价派生：5% 规则收敛到一处，V2 零改动

演示口径（团队决定，不声称商业合理）：`bid_cents = max(1, round(price_cents × 5%))`、`budget_cents = bid_cents × 20`。
5% 与取整**只允许出现在 `src/corpus/pricing.py`**；`bidding/` 目录零改动，
`pipeline_v2.py` 只做 `facts` 透传。

- 免费游戏保底 1 分（`Bid` 要求 `bid_cents ≥ 1`，否则 3 条免费游戏会被静默排除）；
- 预算取"20 次曝光"而非"等于定价"：否则免费游戏预算为 0，且 5% 取整会漂移（$14.99 → 75 分 × 20 > 1499）。

### D6 · 不引入新的外部依赖

无数据库、无向量库、无网络。语料是 JSONL，索引在内存构建；与 V1/V2 的零外部依赖约定一致。

---

## 3. 被否的备选

| 备选 | 为什么否 |
|---|---|
| 新建 `docs3/` 独立目录 | 会让 V3 脱离验证平面（见 D1） |
| 新建 `CorpusAd` 类型并协议化下游 | 要动 `ads`/`compliance` 的冻结层，波及面远大于收益；spike 证明复用 `Ad` 可行 |
| 在 corpus 侧先过滤再进合规 | 破坏"compliance 唯一权威"，与 `INV-ADS-001` 冲突 |
| 直接把 `price_final` 当出价（1:1） | 单位错配：售价是买断价，不是每次曝光的出价 |
| 用 RAG / 向量检索做召回 | 与零外部依赖、确定性可校验冲突；已改为 V4（`scope.out` 的 RAG 条） |

---

## 4. 后果

- 基线需求 **41 → 59 条**，不变量 **19 → 27 条**，架构元素 **8 → 9 个**；
- `compliance` 出现一个新的可选入参，**默认行为不变**，但必须由测试锁定"不传参 = V1 行为"；
- `data/corpus/` 成为新的只读数据源（safety-relevant：内容分级规则的数据来源）；
- 运行时 monitor 仍只在登记层面（`TD-001` 未关闭），V3 不解决该债。

---

## 5. 重开条件（任一触发即重审本 ADR）

1. 语料 `parser_ver` 升版或字段形态变化；
2. 要接真实曝光/计费（CPM/CPC/对账），而非演示级 5%；
3. 要引入向量检索或任何新外部依赖；
4. K 的取值要突破 50（预算上限被改）；
5. 合规需要新增第六步（而非在既有步骤内扩充）。

---

## 人工批准记录

| 项 | 内容 |
|---|---|
| 批准人（具名人类） | ⏳ |
| 批准时间 | ⏳ |
| 结论 | ⏳ `Accepted` / `CHANGES REQUIRED` |

> **No agent may self-approve**（课程 §11.3）。
