# 场景化广告推荐引擎 — V3 需求草案：检索增强（RAG）与真实语料

> 状态：迭代候选 · 2026-10-18
> 定位：在 V1（规则预筛 + LLM 闭集选择）、V2（报价竞价）基础上引入**检索增强的候选生成层**，
> 并将语料从 14 条手工素材替换/扩展为**≥20,000 条真实爬取数据**，输入从纯结构化扩展为**结构化 + 自然语言 query**，
> 输出从单条广告扩展为 **top-N 排序结果 + 逐条匹配理由**。
> 交叉动机：本草案同时覆盖 CS5481（Data Engineering）Topic 1 的五项 Key Task——
> 同一套数据管道与检索代码，两侧课程各取所需（DE 侧聚焦管道与检索实验，SE 侧聚焦治理与权威边界）。
> 轮次纪律：V1/V2 层冻结（IMMUTABLE）；V3 新条目追加到 `docs3/`；V1 全部测试与 V2 增量测试**零回归**仍须全绿。

---

## 0. 为什么 V3 必然要做检索（驱动因子）

不是"想加功能"，而是既有约束被真实语料逼出的推论：

1. **token 预算物理不可行**：`config.yaml` 的 `context_budget_tokens: 2000` + `CandidateBrief` 只带 title——
   14 条候选能塞进 prompt，20,000 条**不可能**。`filter_by_scene` 规则预筛在真实语料上仍会剩数千条 → 必然触发 RP-010 降级。
   **结论：候选集必须从"全量规则筛"变成"检索召回 top-K"，这是唯一能让管道在大语料上活着的设计。**
2. **V3 = RAG 是 ADR-001 的既定占位**（V1 明确"不用 RAG，留 V3"），本草案是兑现。
3. **匹配理由需要证据**：解释"为什么这条匹配 query"必须有可引用的检索信号（BM25 命中词、向量相似度、融合名次），
   纯 LLM 空口理由不可验证，违反本项目"证据链"基因。

---

## 1. V3 决策流程（示意）

```
输入 = 结构化场景（时段/设备/标签）＋ 可选自然语言 query
        ↓
① 输入校验（确定性）：scene schema 照旧；query 为新增自由文本通道 → 长度/字符集上限 + 注入扫描（pre-model）
        ↓
② 检索召回（新架构元素 ⑧ retrieval，确定性为主）：
     规则预筛（V1 保留，作为硬约束前置过滤）
     → BM25 关键词召回（自研索引）＋ 向量 ANN 召回（pgvector/HNSW）
     → RRF 融合 → top-K 候选（K 受 token 预算反推，保证装得进 prompt）
        ↓
③ LLM 相关性建议（V2 语义沿用：只建议，不定序终局）
        ↓
④ （若 V2 已落地）竞价引擎确定性定胜负/成交
        ↓
⑤ 合规过滤（确定性 · FINAL AUTHORITY，顺序不可变）：
     违禁词 / 品类禁忌 / 场景限制 / 审核状态（见 §4 的 revised 语义）
        ↓
⑥ 渲染：top-N 排序列表 + 逐条解释（解释只读，引用检索证据）＋ 审计（含检索快照，可完整 replay）
```

关键设计：**检索改变"候选从哪来"，不改变"谁有最终否决权"。**
compliance 仍在 LLM 之后、渲染之前；检索层无状态、不回读审计（V1 memory-design S1 对检索层同样适用）。

---

## 2. 数据模型新增

### 2.1 语料分层（三层存储，对应 DE Topic 1 · Task 3）

| 层 | 内容 | 存储 |
|---|---|---|
| raw | 爬取原始 JSON（未清洗） | 对象/文件表 `corpus_raw` |
| 结构化元数据 | 清洗后的 item（id/title/描述/品类/来源/抓取时间）+ 富化产物（标签、摘要） | PostgreSQL 表 `corpus_item` |
| 向量 | 每条 item 的 embedding + 索引参数版本 | 同库 `corpus_vector`（pgvector 列 + HNSW 索引） |

### 2.2 新增/修订字段（`corpus_item`，真实语料条目）

| 字段 | 类型 | 说明 |
|---|---|---|
| `item_id` | string | 新命名空间（如 `itm_\d+`），与 `ad_\d+` 并存不复用 |
| `source` | string | 数据来源标识（站点/API），审计与重放需要 |
| `description` | text | 富文本描述（检索的主要载荷，替代 14 条素材的短 copy） |
| `tags[]` / `summary` | JSON 数组 / text | LLM 富化产物（构建期写入，非运行时） |
| `review_status` | enum | `machine_checked / human_approved / pending / rejected`（§4 修订 `banned_check` 后的新状态机） |
| `embedding_model` / `enrich_version` | string | 版本溯源延伸到数据层（换模型必须全量重刷并留版本戳） |

> AD_SCHEMA 不动、不扩：真实语料**不走** `AdRepository` 的逐条校验路径（否则 20,000 条会在 `additionalProperties:false` 上整体加载失败）。
> 新增独立 `CorpusRepository`；只有映射进决策域的子集才投影为 ad 类型。

---

## 3. 需求条目（REQ-040 起，延续 V1/V2 编号）

### 3.1 数据采集与富化（DE Task 1+2）

| ID | 类型 | 需求 | 优先级 | 机器可检查的验收标准 |
|---|---|---|---|---|
| REQ-040 | Functional | 采集 ≥20,000 条带丰富描述的真实条目，入库三层存储 | Must | `corpus_item` 行数 ≥ 20,000；每行描述字段非空且 ≥ 50 字符；采集脚本支持断点续传与去重（重跑行数不增） |
| REQ-041 | Functional | LLM 富化：结构化标签（固定 schema）+ 2–3 句摘要 | Must | 标签为符合登记 JSON schema 的数组；富化产物抽检合法率 ≥ 99%；非法输出重试后仍失败者标记失败、不入库脏值 |
| REQ-042 | Functional | 每条 item 生成 embedding 并存入向量列 | Must | 向量列空值数 = 0；维度与登记模型一致；`embedding_model` 版本戳覆盖 100% 行 |
| REQ-043 | Quality | 富化幂等 + 成本台账 | Must | 同一 `enrich_version` 重复执行零 API 调用（缓存命中）；台账记录 token 用量与费用，误差 = 0 |
| REQ-044 | Security | 爬取文本按不可信输入处理（间接注入防线） | Must | 富化与检索 prompt 装配前，item 文本过注入门；注入样本集检出率 100%；命中条目降级处理不进决策 |

### 3.2 检索与混合召回（DE Task 4 之核心，**必须自研**）

| ID | 类型 | 需求 | 优先级 | 机器可检查的验收标准 |
|---|---|---|---|---|
| REQ-045 | Invariant | BM25 索引为自研实现（允许用分词器，检索打分逻辑自写） | Must | 打分函数代码归属 `src/retrieval/`；单元测试对已知语料手算分数逐位一致 |
| REQ-046 | Invariant | 检索层为确定性纯函数：固定索引 + 固定 query → 输出名次完全一致 | Must | 同输入双跑 diff = 0；RRF 融合含固定 tie-break（如 item_id 升序），禁止随机 |
| REQ-047 | Invariant | 检索不回读审计/会话历史（无状态，沿用 memory-design S1） | Must | `src/retrieval/` 对 `audit` 零 import（fitness function 静态检查） |
| REQ-048 | Functional | 双入口：item_id → top-N 相似；自然语言 query → 排序列表 | Must | 两类接口各有端到端测试；返回条数 = 请求的 N ≤ K 上限 |
| REQ-049 | Functional | 融合召回：BM25 与向量两路结果经 RRF 合并 | Must | 融合实现引用 Cormack et al. 2009 公式；消融实验中融合 Recall@10 ≥ 任一路单用 |
| REQ-050 | Invariant | **检索候选必须全量过 compliance，检索分数不构成任何豁免** | Must | 反例测试：构造"黑名单品类且向量距离最近"的样本，最终展示数 = 0；纳入变异验证 |
| REQ-051 | Functional | top-K 由 token 预算反推：K = 使候选摘要总 token ≤ `context_budget_tokens − 固定开销` 的最大值 | Must | 属性测试：任意语料规模下装配后超限率 = 0（RP-010 不再由大语料触发） |

### 3.3 自然语言查询输入（触发 ADR-001 T3，须修订）

| ID | 类型 | 需求 | 优先级 | 机器可检查的验收标准 |
|---|---|---|---|---|
| REQ-052 | Functional | 输入 schema 扩展：`scene` 必填不变，`query` 为可选自由文本 | Must | 无 query 请求行为与 V1/V2 完全一致（零回归）；有 query 走检索通道 |
| REQ-053 | Security | query 上限与清洗：长度 ≤ 登记值（建议 512 字符），超限拒绝走结构化降级 | Must | 超限样本 100% 返回结构化错误码，不进 prompt |
| REQ-054 | Security | query 侧注入扫描沿用并扩充 pre-model 注入门模式库 | Must | 原 10 条模式全过；新增 query 专用模式（角色劫持/指令覆盖）对自建攻击集检出率 100% |
| REQ-055 | Invariant | query 内容不得改变权威顺序（compliance 恒在 LLM/检索之后） | Must | 结构检查：`retrieval/selector/query` 三者的调用顺序由 pipeline 唯一入口固定，反例注入失败 |

### 3.4 输出与解释（DE Task 5）

| ID | 类型 | 需求 | 优先级 | 机器可检查的验收标准 |
|---|---|---|---|---|
| REQ-056 | Functional | top-N 列表渲染：每项含 item 载荷 + 解释文本 + 检索证据（融合名次/相似分/命中词） | Must | 渲染 schema 校验通过率 100%；每条结果的解释字段非空 |
| REQ-057 | Invariant | 解释路径只读：不得改写排序、不得引入候选集外条目 | Must | 沿用 V1 解释隔离测试模式扩展至列表形态；反例测试纳入变异验证 |
| REQ-058 | Functional | 解释生成仅对最终展示的 top-N（默认 N ≤ 5）在线调用，其余离线/缓存 | Should | 单次请求解释调用次数 ≤ N；P95 解释延迟不拖累检索延迟口径 |

### 3.5 存储与技术边界（修订既有 ADR）

| ID | 类型 | 需求 | 优先级 | 机器可检查的验收标准 |
|---|---|---|---|---|
| REQ-059 | Governance | **ADR-002（无数据库）重开并修订**：新增 PostgreSQL + pgvector 作为向量与元数据载体，经新 ADR 记录 | Must | 新 ADR 文件存在且 Accepted（具名人类批准）；JSON/JSONL 路径仍保留（决策域兼容），双存储边界在 blueprint 登记 |
| REQ-060 | Governance | **ADR-001 T3 触发记录**：自由文本输入落地时按修订流程处理，不得静默绕过 | Must | 修订 ADR 引用 T3 与 INV-ADS-005，给出加强后的验收证据（REQ-053/054） |
| REQ-061 | Invariant | 决策路径数据库连接只读；采集/富化写入走独立构建管道 | Must | 运行时 DB 账号权限为 SELECT-only（配置断言）；写入路径不出现在 `src/app` import 图 |
| REQ-062 | Quality | `retrieval` / `enrichment` 登记为新架构元素，纳入 fitness function | Must | `ELEMENT_BY_PACKAGE` 含两新项（先例：`"bidding"`）；模块↔元素一一对应检查通过 |

### 3.6 性能与可观测（DE low-latency 要求 + 顺手还债）

| ID | 类型 | 需求 | 优先级 | 机器可检查的验收标准 |
|---|---|---|---|---|
| REQ-063 | Performance | 检索单次延迟 P95 < 200ms（20k 规模、本地 Postgres+pgvector、不含 LLM 调用） | Must | live 基准脚本产出 P50/P95；接入 monitor 体系（对齐 TD-001 采集接线） |
| REQ-064 | Performance | HNSW 参数（m/ef_construction/ef_search）显式登记，调参记录进报告 | Should | 参数入库为配置而非代码常量；至少 3 组参数-召回率-延迟对照数据 |
| REQ-065 | Governance | 每次检索请求审计含完整检索快照：query 原文、两路 top-20 与分数、融合后名次、K 值 | Must | 重放该快照可逐位复原 top-K；审计仍"恰好 1 条"契约不变 |

### 3.7 评估双口径（DE Task "experiments" + SE 评估门）

| ID | 类型 | 需求 | 优先级 | 机器可检查的验收标准 |
|---|---|---|---|---|
| REQ-066 | Quality | eval 分区扩展：V3 检索分区与 V1 合规分区并存，现有 25 条用例零回归 | Must | 旧分区达成率不因 V3 下降（Mock 口径）；新分区字段 `retrieval_eval_case_count` 登记 |
| REQ-067 | Functional | 人工标注检索评测集：≥30 条 query（含 5 条以上"无答案"负例） | Must | 每条 query 附相关 item 标注；负例用于测拒答——检索置信不足时输出显式"无匹配"而非硬凑 top-N |
| REQ-068 | Functional | 检索指标报告：Recall@10 / MRR / nDCG@10，BM25-only、vector-only、RRF 三组消融 | Must | 指标脚本一键产出表格；结论写入 CS5481 报告 Experiments 节 |
| REQ-069 | Quality | 切块/embedding 对照（仅当语料含长文本时）：≥2 种策略对 Recall 的影响 | Should | 对照数据存在且口径一致（同一评测集） |
| REQ-070 | Governance | LLM 用于富化/解释的用法在两门课报告中双向披露（模型、prompt、哪些代码自研） | Must | AI-use log 新增条目；CS5481 报告含披露节；DE 侧声明核心管道自研（REQ-045/046 即证据） |

---

## 4. 合规审核的 V3 修订（按"可以改、技术可行"落定）

V1 的 `banned_check ∈ {checked, pending, banned}` 是**人工背书**语义，真实语料上不可负担。V3 改为**双层审核状态机**（REQ 见 §2.2 `review_status`）：

| 状态 | 语义 | 判定来源 | 可否进入候选/展示 |
|---|---|---|---|
| `machine_checked` | 违禁词表 + LLM 合规预检通过 | 构建期管道（确定性词表优先，LLM 仅补充判断，LLM 说"可疑"即降 pending） | **可候选、可展示**——但运行时五步合规管道照旧全量执行，机审预检**不豁免**任何一步 |
| `human_approved` | 人工复核通过 | 流程侧（仅小规模重点条目） | 可 |
| `pending` / `rejected` | 未过预检 / 明确违规 | 构建期 | fail-closed，不可 |

要点：预检发生在**构建期**，不新增运行时状态；运行时权威仍只有 compliance。
违禁词命中判定沿用 V1 的确定性规则（最长优先→码点序），LLM 只作召回补充、不作放行依据——
**"AI 是顾问，代码是执行官"在审核环节的同构复刻**。此项变更触碰 `INV-ADS-001` 边界，须走 ADR + 人工批准（对应 REQ-037 同款治理，V3 中重申）。

---

## 5. 硬性不变量清单（给测试/变异验证的抓手）

- **一条权威链**：`retrieval → selector → (bidding) → compliance → render`，顺序不可颠倒，任何输入（含 query 文本）不可绕过（REQ-055/050）
- **两条无状态**：检索不回读审计（REQ-047）；同索引同 query 输出确定（REQ-046）
- **两条 fail-closed**：`pending/rejected` 永不展示；预检与运行时合规任一失败即 no_ad / 剔除出列表
- **一条预算恒等**：K 值由 token 预算反推，装配超限率 = 0（REQ-051）
- **一条证据完整**：检索快照可逐位重放（REQ-065）
- 每条不变量 ≥1 反例测试，接入 `mutation_check.py`；流程类不变量（人审环节）单独登记为不可变异覆盖，沿用 V1 对 INV-ADS-009/010/011 的处理先例。

---

## 6. CS5481 Topic 1 覆盖对照（双用途证明)

| DE Key Task | V3 需求 | 备注 |
|---|---|---|
| ① Ingestion ≥20k | REQ-040/043 | 真实语料替换模拟数据 |
| ② LLM Enrichment | REQ-041/042/044 | 标签+摘要+embedding |
| ③ Data Management | REQ-059/061 + §2.1 三层 | PostgreSQL+pgvector，满足作业"appropriate database" |
| ④ Hybrid Retrieval | REQ-045~051/063~064 | 自研 BM25 + ANN + RRF + 低延迟 |
| ⑤ Explanation | REQ-056~058 | 每条匹配理由 + 检索证据 |
| Experiments | REQ-066~070 | 消融 + Recall/MRR/nDCG + AI 披露 |

交付边界建议（防跨课重复提交质疑）：**代码共享，报告分写**——SE 报告聚焦权威链、不变量、治理修订（ADR-001 T3 / ADR-002 重开 / 审核状态机）；DE 报告聚焦管道、检索实验与指标。两侧互相引用对方版本号为"同源工程"，并在开工前向两门课讲师披露复用范围。

---

## 7. 待讨论

- [ ] 领域拍板：商品 / 游戏 / 图书？建议选**有公开 API 且描述富文本**的域（IGDB/TMDB/OpenLibrary），先半天验证 20k 可得再全员 all-in
- [ ] V3 与 V2 的落地顺序：检索层不依赖竞价（正交），但都触碰 pipeline；建议 V2 先行解冻两个设计冲突，V3 并行做构建期（采集/富化/索引）——构建期不动运行平面，可提前开工
- [ ] K 与 N 的默认值：top-K 进 prompt（受 2000 token），top-N 展示（建议 N ≤ 5，解释成本随 N 线性）
- [ ] 向量库选型定案：pgvector（一个库全包，REQ-059 最简）vs Qdrant（专用，运维多一个组件）
- [ ] BM25 自研深度：手写倒排 + 打分（最贴"core pipeline 自研"红线）vs 用现成检索引擎仅自写融合——建议前者，DE 侧经得起追问
- [ ] 富化模型与 embedding 供应商：与 OQ-001（LLM 供应商）合并决策，本地开源 embedding（BGE 类）可让 20k 条成本近零
- [ ] "无答案"负例的置信阈值：向量相似度低于多少判定"知识库不含答案"（对应 DE 要求的显式拒答）

---

## 8. 版本演进备忘

| 版本 | 内容 | 状态 |
|---|---|---|
| V1 | 规则预筛 → LLM 闭集选择 → 合规过滤 → 渲染（无 RAG、无竞价） | 基线，已冻结 |
| V2 | + 报价竞价：LLM 降为相关性建议，竞价引擎确定性定胜负 | 候选（`requirements-v2-bidding-draft.md`），有两个未决设计冲突 |
| V3 | + 检索增强：真实语料 ≥20k、三层存储、自研 BM25+ANN+RRF、自然语言 query、top-N 带证据解释、双层机审 | **本文件（需求候选）** |

> V3 启动前置（缺一即返工）：① 新 ADR 修订 ADR-002（数据库）；② ADR-001 T3 触发处理记录；③ 审核状态机变更获批；
> ④ `docs3/` 轮次边界确认（照 V2 的 `docs2/` 惯例）；⑤ 领域拍板与数据可得性验证。
