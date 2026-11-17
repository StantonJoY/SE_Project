# V3 需求规格（正式稿）· 真实语料接入

> **状态**：待人工批准（PR-0 录入注册表后转为 `approved`）
> **轮次**：V3（`version: "V3"`）· **文档位置**：沿用 V2 先例，在 `docs/` 原地增量
> **草案来源**：`V3req初稿.md` / `迭代的三挡要求初稿.md`（仓库外）+ `V3spike结论.md` 的实测结论
> **编号说明**：本文件的 `REQ-V3-SE-NN` 是**草案标签**，只用于讨论；录入注册表时统一映射为
> 延续 ADS 编号的正式 ID（见 §1 表格第三列）。原因：`scripts/validate_requirements.py` 的
> `type_family` 要求 ID 族前缀与 `type` 相容，`REQ-V3-SE-01` 无法通过校验。

---

## 0. 定位

**一句话**：在 V1/V2 冻结层之上，把 14 条手写素材替换为 Steam 真实语料——
新增只读 `CorpusRepository` 与投影适配器，候选生成改为确定性标签匹配，
在既有五步合规管道内扩充"内容标签并集 + 年龄兜底"两套判据。
**权威链不变、输出仍为单条、零回归。**

**为什么这一轮值钱**（spike 实测，见 `V3spike结论.md`）：

1. 真实语料**能**通过现有 `AD_SCHEMA` 与 `AdRepository`（30/30），不需要新类型；
2. 但现有合规对真实语料**零拦截**（30 条全部放行，其中 17 条带暴力/血腥/性/毒品标记）；
3. 只看 `content_descriptors` 会漏 7/30（Among Us 的 descriptors 为空但 warnings 有 Blood）；
4. 27 条 `required_age=0` 中有真实限制项（CS2 是 0 但 `[2,5]`）——年龄兜底只能是第二位。

### 显式不做

- BM25 / 向量 / embedding / pgvector / Rerank / 自然语言 query（`scope.out` 的 RAG 条迁移到 V4 或 withdrawn，PR-0 处理）
- 爬取与富化管道、双层审核状态机
- 修改 `AD_SCHEMA`、修改 `AdRepository` 的行为
- `description_clean` 进 prompt（最长 8,007 / 全量 63,404 字符）
- top-N 列表输出、解释证据化、FTS5（deferred，见 §5）

---

## 1. 需求条目（15 条）

> 类型/优先级取值受 `req-schema.json` 约束：`functional | invariant | quality | performance | cost | governance | security`；`must | should | could | wont`。

### 1.1 语料接入与投影

| 草案标签 | 正式 ID | 类型 | 需求 | fit criterion（机器可检查） |
|---|---|---|---|---|
| REQ-V3-SE-01 | `REQ-ADS-FR-009` | functional | 新增**只读** `CorpusRepository`，从 `items.jsonl` + `tags.jsonl` 加载，只加载轻字段（`item_id/name/genres/native_tags/summary/required_age/content_descriptors/review_count` + 七维 tags），**不加载 `description_clean`** | 加载 30 条样本成功且行数一致；加载对象**不含** `description_clean` 属性；`src/corpus/` 对 `audit`/`selector`/`compliance` 零 import（fitness 静态检查） |
| REQ-V3-SE-02 | `REQ-ADS-ARCH-013` | invariant | 语料与手写素材**双源并存**：投影产物必须通过 `AD_SCHEMA` 与 `AdRepository` 校验；扩展信息（七维标签/内容标识/警告/年龄）**走旁路映射**，不进 `Ad` 对象、不扩 `AD_SCHEMA` | 30 条投影全部通过 `AD_SCHEMA`（spike 已实测 30/30）；向 `AdRepository` 传入含额外字段的原始 item 必失败；14 条手写素材路径单独用例全过 |
| REQ-V3-SE-03 | `REQ-ADS-FR-010` | functional | 投影适配器 `corpus_to_ad(item, tags)`：`ad_id = "ad_" + item_id`、`title = name`、`copy = summary`、`category` 三级兜底（`tags.genre[0]` → `items.genres[0]` → `"Uncategorized"`）、`scene_restrictions` 取默认全放开、`banned_check = "checked"` | 逐字段映射单测；**必须覆盖 `genres=[]` 的两条真实样本（241930、71250）**，断言 category 落到 `tags.genre` 而非 `Uncategorized`；`ad_id` 全部匹配 `^ad_[0-9]+$` |

### 1.2 确定性候选生成

| 草案标签 | 正式 ID | 类型 | 需求 | fit criterion |
|---|---|---|---|---|
| REQ-V3-SE-04 | `REQ-ADS-FR-011` | functional | 候选生成保留 V1 规则预筛作为硬约束前置；新增配置化 `场景标签 → 语料标签` 映射；按「命中 `tags` + `native_tags` 总数降序 + `item_id` 升序」取 top-K（**K=30，配置化**） | 同输入双跑 diff = 0；K 从 `config.yaml` 读取；空匹配返回 `[]`；不依赖 `review_count` 连续值（二值字段） |
| REQ-V3-SE-05 | `REQ-ADS-ARCH-014` | invariant | 候选生成是**确定性纯函数**：不回读 audit、不读会话历史、不依赖时间/随机数 | `src/corpus/` 对 `audit`/`random`/`time` 零 import；双跑 diff = 0；纳入 `mutation_check.py` |
| — | `REQ-ADS-NFR-COST-002` | cost | **K 的上限由上下文预算反推**：2000 token 预算下 K=30 占 58%，K=60 超预算（108%） | 配置校验拒绝 K > 50；`eval` 记录实际 token；超预算时降级 `budget_exceeded` 而非截断候选 |

### 1.3 合规扩展（防坑核心）

| 草案标签 | 正式 ID | 类型 | 需求 | fit criterion |
|---|---|---|---|---|
| REQ-V3-SE-06 | `REQ-ADS-ARCH-015` | invariant | 合规管道**步骤数与顺序不变**（`output_exists → banned_words → banned_check → category → scene`）；新增规则只能作为既有步骤内部的规则扩充 | 管道步骤列表与 V1 逐位一致（diff = 0）；fail-closed 语义不变 |
| REQ-V3-SE-07 | `REQ-ADS-NFR-SAFETY-008` | invariant | **主判据（内容）**：`content_warnings ∪ 映射后的 content_descriptors` 与场景禁项求交集 → 命中即拒 | 反例：`730`（CS2，age=0 但 `[2,5]`）在 `family` 场景**必须被拒**；`945360`（Among Us，descriptors 空但 warnings=[Violence,Blood]）在 `family` 场景**必须被拒**（证明只用 descriptors 会漏） |
| REQ-V3-SE-08 | `REQ-ADS-NFR-SAFETY-009` | invariant | **兜底判据（年龄）**：`required_age` 超过场景上限 → 拒；上限走配置，不硬编码 | 表驱动覆盖每个场景上限；`359550`（R6S，age=17）在 `campus` 被拒、在 `competitive` 通过 |
| REQ-V3-SE-09 | `REQ-ADS-NFR-SAFETY-010` | invariant | 三档场景内容分级：`family`（严）/ `campus`（中）/ `competitive`（宽），禁项表配置化 | 表驱动：`413150` Stardew 三档全过；`730` CS2 仅 `competitive` 过；`265210` Viscera 三档全拒 |
| REQ-V3-SE-10 | `REQ-ADS-SEC-003` | security | 语料文本（`name`/`summary`/标签）视为不可信；进 selector prompt 前必须过既有 pre-model 注入门 | 既有注入模式全部仍命中；构造含注入模式的语料样本，命中则不进 prompt；检出率 100% |

### 1.4 回归、评估与治理

| 草案标签 | 正式 ID | 类型 | 需求 | fit criterion |
|---|---|---|---|---|
| REQ-V3-SE-11 | `REQ-ADS-NFR-QA-005` | quality | **零回归**：V1+V2 全部 617 个离线测试全绿；旧 25 条 eval 达成率不下降 | CI 全绿；旧分区 replay 报告与 V2 基线 diff = 0；测试数 ≥ 617 |
| REQ-V3-SE-12 | `REQ-ADS-NFR-QA-006` | quality | eval 新增 V3 分区：**12–15 条**真实语料场景用例，含 ≥3 条无匹配负例；旧分区不变 | 新分区 `case_count` 登记；负例 100% 走显式无匹配语义（不硬凑 top-K） |
| REQ-V3-SE-13 | `REQ-ADS-GOV-004` | governance | 新增 `ADR-006`《V3 轮次接入与真实语料边界》，记录：只读、投影旁路、不扩 AD_SCHEMA、合规只动 2 个函数、权威链不变、语料不可信、轮次目录沿用 | ADR 存在且 **Accepted（具名人类批准）**；`check_safety_paths.py` 解析通过 |
| REQ-V3-SE-14 | `REQ-ADS-NFR-QA-007` | quality | `corpus` 登记为**新架构元素**并纳入 fitness | `ELEMENT_BY_PACKAGE` 含 `"corpus"`；`fitness_functions.py` 通过；依赖方向单向 |
| REQ-V3-SE-15 | `REQ-ADS-GOV-005` | governance | 合规扩展属 safety-critical：**测试必须先于实现获批**；同步更新 `invariants.md`/`trace-matrix`/`acceptance-coverage-map`/`ai-use-log` | `check_test_approval.py` 通过（新增 `TA-0005`）；四个工件均有 V3 条目；`check_ai_use_log.py` 通过 |

---

## 2. 不变量与反例（给 mutation_check 的抓手）

| 不变量 | 反例（必须能失败） |
|---|---|
| 权威链顺序不变（ARCH-015） | 把 `check_scene` 挪到 `check_output` 之前 → 顺序契约测试必须红 |
| 语料不进 Ad 契约（ARCH-013） | 给 `AdRepository` 喂带 `content_descriptors` 的原始 item → 必须抛 `AdLoadError` |
| 候选生成确定性（ARCH-014） | 注入 `random.shuffle` 或读 `time` → 双跑 diff 测试必须红 |
| 内容并集判据（NFR-SAFETY-008） | 删掉 ∪ 的 warnings 一侧 → Among Us 在 family 场景放行 → 反例必须红 |
| 年龄兜底（NFR-SAFETY-009） | 把上限硬编码为 18 → R6S 在 campus 放行 → 反例必须红 |
| 不加载长文本（FR-009） | 在 `CorpusRepository` 里加载 `description_clean` → 结构断言必须红 |
| 注入门前置（SEC-003） | 语料样本含注入模式但直接进 prompt → 测试必须红 |

---

## 3. 与现有工件的关系

| 文件 | 动作 | 是否受保护 |
|---|---|---|
| `src/corpus/`（新包，4 个文件） | 新增 | 否 |
| `src/compliance/pipeline.py` | `run_compliance` 加可选 `facts` 参数；`check_scene` 读它 | **是（须 ADR-006）** |
| `data/scene-content-rules.yaml` | 新增三档禁项表 | **是（ADR-005 同族，须 ADR-006 覆盖）** |
| `config.yaml` | 新增 `corpus` 段（路径、K、场景标签映射） | 否 |
| `docs/req/requirements.yaml` | 追加 15 条 + 改 `scope.out` 的 RAG 条 + `evolution_rounds` 加 V3 | **是（须 ADR-006）** |
| `docs/architecture/invariants.md` | 追加 6 条 V3 不变量 | **仅只读（须人工批准）** |
| `docs/architecture/trace-matrix.md` | 追加 V3 行 + monitor | 否 |
| `docs/code-governance/acceptance-coverage-map.yaml` | 追加 V3 覆盖去向 | **是（须 ADR-006）** |
| `scripts/fitness_functions.py` | `ELEMENT_BY_PACKAGE` 加 `corpus` | **是（须 ADR-006）** |
| `eval/eval_cases.json` + `eval_runner.py` | 新增 V3 分区 | **是（须 ADR-006）** |
| `docs/ai-use-log.yaml` | 追加 V3 条目 | 否 |

> 受影响面比想象小：合规 6 个函数里**只动 2 个**（`run_compliance` + `check_scene`），其余 4 个签名不变。

---

## 4. 已定的决策（原草案的 4 个待确认点）

| # | 问题 | 决定 | 依据 |
|---|---|---|---|
| 1 | 三档场景默认值 | 采纳草案：`family` 拒 Violence/Blood/Gore/Sexual/Nudity/Drugs；`campus` 拒 Gore/Sexual/Nudity/Drugs；`competitive` 仅拒 Nudity | 与样本实况一致 |
| 2 | K 默认值 | **30** | 实测 1152 token / 2000（58%）；K=60 超预算 |
| 3 | 注入门是否新增模式 | **先用既有门**，不新增；加一条语料反例测试 | 现有 10 条模式已覆盖；新增模式需重标定评估口径 |
| 4 | 负例语义 | **先复用 `no_ad`**，`no_match` 进 deferred | 避免同时改渲染 schema |

---

## 5. Deferred（不进本轮）

| 条目 | 原因 |
|---|---|
| 解释证据化（引用 item_id + 命中标签） | 成本低但非阻塞；若有余力**建议提前**（叙事价值最高） |
| top-3 列表输出 | 需改 render 判别联合，风险高于收益 |
| 独立 `no_match` reason code | 与 `no_ad` 语义暂可合并 |
| `review_count` 末位 tie-break | 二值字段，区分度低 |
| SQLite FTS5 / `price_final` 接 V2 / token 反推 K / 消融实验 | 全部 V4 及以后 |
