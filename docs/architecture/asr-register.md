# ASR 登记册（Architecturally Significant Requirements Register）

> **A1 产物** · 对应课程 `3. 软件架构.md` §3.1（P13）
> 状态：**草案待人工批准** · 版本：V1 轮次 · 生成日期：2026-10-06
> 输入：`docs/req/requirements.yaml`（RE 制品）
> 下游：本文件 → `docs/architecture/invariants.md`（A2）、`docs/architecture/adr/001-guarded-hybrid.md`、`architecture-blueprint.md`
>
> **课程警告（note 行 1194）**：本登记册的字段与格式由 CS5351 自创，非通用标准。审计按课件格式，不按通用 ADR/C4 惯例。

---

## 0. 本文件回答什么

A1 回答一个问题：**哪些 RE 需求强制了结构决策**（wrapper / gate / path / checkpoint / permission），
哪些只是实现细节。

> 课程判据（note 行 278）：需求在强制 **State**（pause、resume、checkpoint）、**Authority shift**（human takes over）、
> **Evidence obligation**（who、what、when）、**Structural element**（wrapper、gate、path）、**Permission**（who may call what）
> 时为架构性；**阈值 > 1 aspect altered ＝ ASR**。
>
> 经验法则（note 行 317）：若需求在架构中强制一个 box、gate、path 或 checkpoint，很可能是 ASR；
> **若一句 if-statement 就能轻松实现，则很可能不是**。

> **本项目的关键差异（必须显式声明）**：VHIS 是"理赔裁决"，有 `REVIEW` 这个人类复核终态，
> 因此它的 fallback 是 fail-closed 的 `REVIEW`。**本项目没有运行时的人类复核环节**，
> 降级终点是 `no_ad`（不展示任何广告）。`no_ad` 同样是 fail-closed——不展示 = 安全默认。
> 该映射的理由与风险见 `invariants.md` §1 与 §4（风险 R-001）。

---

## 1. 五维 Litmus 判定表（V1 全量）

维度定义取自课程 §2.2（note 行 223–229）：
**St** = State ／ **Auth** = Authority shift ／ **Ev** = Evidence ／ **Struct** = Structural element ／ **Perm** = Permission。

**判定规则：命中 ≥ 2 维 → ASR；0–1 维 → implementation。**

| REQ ID | 需求摘要 | type | St | Auth | Ev | Struct | Perm | 命中 | 判定 | Tactic | ASR ID |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|---|---|
| `REQ-ADS-FR-001` | 从本地 JSON 加载素材库 | functional | – | – | – | ✅ | – | 1 | **impl** | 加载器，无结构 | — |
| `REQ-ADS-ARCH-001` | 素材字段完整且合法（schema） | invariant | – | ✅ | ✅ | ✅ | – | 3 | **ASR** | schema gate（加载期整批 fail-closed） | `ASR-ADS-01` |
| `REQ-ADS-FR-002` | 场景输入校验后方可进入流程 | functional | – | – | – | ✅ | – | 1 | **impl** | 校验函数 | — |
| `REQ-ADS-ARCH-002` | LLM 闭集选择，不得越出候选集 | invariant | – | ✅ | ✅ | ✅ | – | 3 | **ASR** | 候选集 wrapper + 存在性 gate | `ASR-ADS-02` |
| `REQ-ADS-ARCH-003` | LLM 输出必须为合法结构化 JSON | invariant | – | ✅ | ✅ | ✅ | – | 3 | **ASR** | validation gate + fail-closed | `ASR-ADS-03` |
| `REQ-ADS-NFR-SAFETY-001` | 展示广告 100% 通过确定性合规过滤 | invariant | – | ✅ | ✅ | ✅ | – | 3 | **ASR** ⭐ | **deterministic wrapper（核心）** | `ASR-ADS-04` |
| `REQ-ADS-NFR-SAFETY-002` | 敏感品类禁止展示 | invariant | – | ✅ | ✅ | ✅ | – | 3 | **ASR** | 独立 blacklist gate | `ASR-ADS-05` |
| `REQ-ADS-NFR-SAFETY-003` | 含违禁词广告禁止展示 | invariant | – | – | ✅ | ✅ | – | 2 | **ASR** | pre-display gate | `ASR-ADS-06` |
| `REQ-ADS-NFR-SAFETY-004` | 不违反自身声明与规则级场景限制 | invariant | – | ✅ | ✅ | ✅ | – | 3 | **ASR** | 双层 gate（预筛 + 终检） | `ASR-ADS-07` |
| `REQ-ADS-NFR-SAFETY-005` | 低置信度不得直接展示 | invariant | ✅ | ✅ | ✅ | ✅ | – | 4 | **ASR** | threshold gate + fallback path | `ASR-ADS-08` |
| `REQ-ADS-FR-003` | 无候选/失败/全拒 → 降级 no_ad | functional | ✅ | ✅ | ✅ | ✅ | – | 4 | **ASR** | fallback path + 原因码 | `ASR-ADS-09` |
| `REQ-ADS-FR-004` | 渲染输出结构化结果（两形态） | functional | – | – | – | ✅ | – | 1 | **impl** | 序列化函数 | — |
| `REQ-ADS-GOV-001` | 每次请求恰好 1 条审计日志、字段完整 | governance | ✅ | – | ✅ | ✅ | – | 3 | **ASR** | provenance 证据子系统 | `ASR-ADS-10` |
| `REQ-ADS-NFR-PERF-001` | 端到端 p95 ≤ 5s，**违规必须被处理** | performance | – | ✅ | ✅ | ✅ | – | 3 | **ASR** ⚠️ | **timeout gate + fallback + p95 监控 + drift alert** | `ASR-ADS-11` |
| `REQ-ADS-ARCH-004` | 确定性部分可复现，零差异 | invariant | – | – | – | ✅ | – | 1 | **impl** | 纯函数即可 | — |
| `REQ-ADS-SEC-001` | LLM 输出不得含可执行指令/提示注入 | security | – | ✅ | ✅ | ✅ | – | 3 | **ASR** | pre-model sanitize gate + 输出校验 | `ASR-ADS-12` |
| `REQ-ADS-GOV-002` | 代码/Prompt 变更须更新 AI-use 日志 | governance | – | ✅ | ✅ | – | ✅ | 3 | **ASR** | permission + pre-commit hook | `ASR-ADS-13` |
| `REQ-ADS-NFR-COST-001` | 单次推荐 token 有上限 | cost | – | ✅ | ✅ | ✅ | – | 3 | **ASR** | budget route + summarization gate | `ASR-ADS-14` |
| `REQ-ADS-NFR-QA-001` | 内置固定评估集（≥20 条，可 replay） | quality | – | – | ✅ | ✅ | – | 2 | **ASR** | 评估 gate（CI，阻断合并） | `ASR-ADS-15` |
| `REQ-ADS-NFR-QA-002` | 每条 fit criterion ≥1 测试；不变量 ≥1 失败测试 | quality | – | ✅ | ✅ | – | ✅ | 3 | **ASR** ⭐ | verification gate（**流程不变量**） | `ASR-ADS-16` |

**统计：22 条基线 RE 需求 → 18 ASR + 4 implementation。**

其中 §1 的 20 条原始需求产出 16 条 ASR；§2.1 的 2 条 A3 承载需求（`REQ-ADS-AI-001`、`REQ-ADS-AI-002`）各产出 1 条 ASR，合计 18 条。
V2 候选需求的 A1 预判见 §9（归属 `docs2/` 轮次，本文件不为其建立正式条目）。

⚠️ **`REQ-ADS-NFR-PERF-001` 是课程明确的"性能陷阱"**（note 行 590）。学生常答 NO。
陷阱在于：**当违规必须被处理时，延迟阈值就是架构性的**。它强制四个结构元素：
`timeout gate`、`fallback path`（degrade → `no_ad`）、`p95 延迟监控`、`SLA drift alert`。
**无 fallback 则需求未实现。**

---

## 2. ASR 明细（V1 共 18 条）

### 2.1 A3 承载需求对应的 ASR（由 §3 落地为需求）

| ASR ID | 来源 REQ | **强制出的结构元素** | Concern Cluster |
|---|---|---|---|
| `ASR-ADS-A3-02` | `REQ-ADS-AI-001` | 解释路径与决策路径**结构分离**；解释评估器独立；解释不得写回 `ad_id` | Closed-Set Selection & Context |
| `ASR-ADS-A3-03` | `REQ-ADS-AI-002` | `pre_write_hook()` + 配置捕获（model/prompt/threshold 版本） | Evidence & Traceability |

### 2.2 由 §1 判定表产出的 ASR

每条给出：强制出的结构元素、所属 concern cluster（A5 输入）、对应 VHIS 参照。

| ASR ID | 来源 REQ | **强制出的结构元素** | Concern Cluster | VHIS 参照 |
|---|---|---|---|---|
| `ASR-ADS-01` | `REQ-ADS-ARCH-001` | 加载期 schema gate；整批 fail-closed（不跳过单条） | Input Contract | — |
| `ASR-ADS-02` | `REQ-ADS-ARCH-002` | **候选集 wrapper**：LLM 只能看见候选集；存在性 gate 拦截集外 ID | Closed-Set Selection | `ARCH-001` |
| `ASR-ADS-03` | `REQ-ADS-ARCH-003` | 严格 JSON validation gate；解析失败 fail-closed | Closed-Set Selection | `INV-002` |
| `ASR-ADS-04` ⭐ | `REQ-ADS-NFR-SAFETY-001` | **确定性 compliance wrapper**（**五步**纯函数管道），位于 AI **之后** | Deterministic Authority | `NFR-SAFETY-001`、`NFR-001` |
| `ASR-ADS-05` | `REQ-ADS-NFR-SAFETY-002` | 独立品类 blacklist gate（与违禁词 gate 分离，便于单独审计） | Deterministic Authority | `NFR-SAFETY-002` |
| `ASR-ADS-06` | `REQ-ADS-NFR-SAFETY-003` | pre-display 违禁词 gate，作用于 title + copy 全量 | Deterministic Authority | `SEC-001` 族 |
| `ASR-ADS-07` | `REQ-ADS-NFR-SAFETY-004` | 双层 gate：预筛（候选集构建）+ 终检（compliance.check_scene） | Deterministic Authority | `NFR-SAFETY-001` |
| `ASR-ADS-08` | `REQ-ADS-NFR-SAFETY-005` | confidence threshold gate + 降级路径 | Degradation & Cost | `NFR-001` |
| `ASR-ADS-09` | `REQ-ADS-FR-003` | **fallback path 集合** + 结构化原因码 | Degradation & Cost | `FR-002` |
| `ASR-ADS-10` | `REQ-ADS-GOV-001` | provenance 证据子系统（场景/候选规模/LLM 原始输出/过滤结果/最终输出） | Evidence & Traceability | `GOV-001` |
| `ASR-ADS-11` ⚠️ | `REQ-ADS-NFR-PERF-001` | **timeout gate + fallback path + p95 监控 + SLA drift alert** | Degradation & Cost | `NFR-PERF-001` |
| `ASR-ADS-12` | `REQ-ADS-SEC-001` | **pre-model sanitize gate** + 输出侧校验（防御纵深两层） | Deterministic Authority | `SEC-001` |
| `ASR-ADS-13` | `REQ-ADS-GOV-002` | permission model（谁可改哪些文件）**AND** pre-commit hook（事件触发拦截） | Evidence & Traceability | `GOV-002` |
| `ASR-ADS-14` | `REQ-ADS-NFR-COST-001` | `route_budget()` 三档路由 + summarization gate + budget monitor | Degradation & Cost | `NFR-COST-001` |
| `ASR-ADS-15` | `REQ-ADS-NFR-QA-001` | 固定评估集 + replay runner，作 CI 阻断门 | Evidence & Traceability | `NFR-002` 族 |
| `ASR-ADS-16` ⭐ | `REQ-ADS-NFR-QA-002` | verification gate：fit criterion 覆盖 + 不变量失败测试（**流程不变量**） | Evidence & Traceability | — |

> **ASR-ADS-13 的机制区分**（note 行 599 强调）：**Permission 定义 WHO，Hook 强制 WHEN；
> 两者都需要，单独任何一个都不够。** 只写权限文件而无 hook，等于只声明不拦截。

---

## 3. A3 新增 ASR（RE 未捕获，源自部署 AI 组件）

> 课程 §3.3（note 行 453）：这三个 ASR 是 **EMERGENT** 的——源于**部署 AI 组件**而非仅来自业务领域；
> 每个 LLM-based 系统都必须处理，**忽略它们不是实现选择，而是架构风险**。

| ASR ID | 名称 | Why RE Does Not Capture It | 强制出的结构元素 | Fit Criterion |
|---|---|---|---|---|
| `ASR-ADS-A3-01` | **Token Budget** | RE 只说 "有上限"，未给路由逻辑与压缩策略 | `route_budget()` 三档（DIRECT / SUMMARIZE / REVIEW）+ summarization gate + token counter + budget monitor | 单次推荐 token ≤ 预算；超 85% 触发 compaction；**compaction 后重新注入 standing constraints** |
| `ASR-ADS-A3-02` | **Explanation Quality** | RE 只有自由的 `reason` 字段，无质量维度、无路径隔离 | **独立解释路径**（结构上独立于决策路径）+ 独立解释评估器 + 「解释失败 ≠ 决策失败」 | 每条被评估的推荐：解释与候选集证据一致；解释路径失败不改写决策结果 |
| `ASR-ADS-A3-03` | **Traceability（结构性强制）** | RE 只说 "记日志"，无 hook、无证据格式 | `pre_write_hook()` 拦截 safety-critical 文件的无 ADR 变更 + 证据记录格式（model / prompt / threshold 版本捕获） | 对 safety-critical 文件零未记录变更；每条决策记录含模型与 prompt 版本 |

### 3.1 `ASR-ADS-A3-01` 的分层上下文结构（课程 §8.4 P163–165）

课程要求 AI 组件的**六层提示架构**与**五步装配管线**。本项目是**单轮闭集选择**（无会话历史），
因此六层**按需裁剪**，不适用层必须显式声明"不适用 + 理由"，而非沉默省略：

| # | 层（课程） | 本项目对应内容 | 预算 | 裁剪策略 |
|---|---|---|---|---|
| 1 | SYSTEM（永不裁剪） | 身份与输出契约：广告选择器，只许输出 schema 内 JSON | ~150 tok | 静态，永不裁剪 |
| 2 | INSTRUCTIONS（永不裁剪） | standing constraints：只能从候选集选、禁止自创文案、**这些约束在 compaction 后必须重新注入** | ~200 tok | 仅随 ADR 修订变化 |
| 3 | RETRIEVED（按相关性裁剪） | 候选集摘要（`ad_id` / category / target_tags） | ~300 tok | 候选超预算时按场景相关性裁剪 |
| 4 | HISTORY（满则压缩） | **不适用**——V1 为无状态单轮，无历史。理由：见 `scope.out` 多轮上下文记忆 | 0 | — |
| 5 | STATE（resume 时注入） | 当前场景特征（time_slot / device / user_tags） | ~100 tok | 每轮注入 |
| 6 | USER MESSAGE（始终存在） | 本次选择任务 | ~50 tok | 每轮刷新 |

**五步装配管线**（在任何 LLM 调用前运行）：`DEDUPLICATE`（候选摘要去重）→
`PRIORITIZE`（System/Instructions 永不丢；候选按相关性）→ `BUDGET`（计数，达窗口 **85%** 触发）→
`COMPACT`（压缩候选摘要）→ `ASSEMBLE`（按优先级拼接）。

> **Re-Injection 是本 ASR 的安全要害**（课程 P165）：compaction 会把 Instructions 推到低注意力位置，
> 导致"规则存在但不可见"（课程实测约束满足率从 98% 降到 72%）。
> 因此 **compaction 之后必须重新注入层 2 的 standing constraints**，且这在架构上是 budget 步骤的强制行为，**不是用户命令**。

### 3.2 `ASR-ADS-A3-02` 的解释路径隔离

课程 INV-004 的对应物：**解释路径绝不能影响决策**。

```
场景 + 候选集 ─┬─ 决策路径  → 闭集选择 → compliance gate → ad_id（权威）
               └─ 解释路径  → 生成 reason → 解释质量评估 → reason 文本（建议性）
                    （二者结构分离；解释失败不得回写决策；解释不得绕过 compliance）
```

**已确认的领域口径（原假设 A-01，2026-10-06 由人类决策关闭 `OQ-009`）**：

VHIS 有明确的"被解释对象"（拒赔理由）。广告推荐系统的解释对象经人类确认为
**「为什么选这条广告」** —— 即解释须说明在**当前场景特征**下，为什么选择该广告
而非候选集中的其他广告。据此，`ASR-ADS-A3-02` 的三条约束为：

- 解释内容**不得作为展示决策的依据**（`INV-ADS-004`）；
- 解释**不得包含未通过 compliance 的文案**（防绕过 gate 泄露违禁内容，`INV-ADS-007` 的复查）；
- 解释质量不达标时**只降级解释**（返回结构化摘要），**不影响 `ad_id`**。

> **该口径对实现的影响**：解释的生成必须能引用「候选集中其他广告」作为对照，
> 因此 `src/selector/` 的解释路径**需要候选集可见**——但**只读**，不得写决策变量。

---

## 4. 被判为 implementation 的 4 条（附理由）

| REQ ID | 需求 | 命中维度 | 为什么不是 ASR |
|---|---|---|---|
| `REQ-ADS-FR-001` | 素材库加载 | 1（Struct） | 文件读取 + 反序列化；除加载期 schema gate（已由 `ASR-ADS-01` 承担）外无结构产出 |
| `REQ-ADS-FR-002` | 场景输入校验 | 1（Struct） | 枚举校验 + 去重；一句校验语句可满足 |
| `REQ-ADS-FR-004` | 渲染输出两形态 | 1（Struct） | 序列化函数；schema 已由输出契约固定 |
| `REQ-ADS-ARCH-004` | 确定性可复现 | 1（Struct） | 纯函数 + 无全局状态即可满足，不强制新元素 |

> 保留理由（note 行 159）：**并非所有 FR/NFR 都是 ASR**；判据是"是否强制一个 box、gate 或 path"，
> 否则属 implementation。这 4 条仍是正式需求，只是**不构成架构驱动因子**。

---

## 5. A5 预输入：Concern Cluster

> 课程 §3.5（note 行 470）：把共享同一架构 concern 的需求**聚类**；用 **concern（而非 requirement ID）命名** cluster；
> 每个 cluster 映射到一个**独立架构职责**；给 cluster 排优先级。

| # | Concern Cluster | 覆盖 ASR | 独立架构职责 | 优先级 |
|---|---|---|---|---|
| 1 | **Deterministic Authority & Compliance** | 04, 05, 06, 07, 12 | 权威边界：AI 之后的确定性强制层 | **1** |
| 2 | **Closed-Set Selection & Context** | 02, 03, 14, A3-01, A3-02 | 建议层：闭集选择 + 上下文装配 | **3** |
| 3 | **Evidence & Traceability** | 10, 13, 15, 16, A3-03 | 证据层：审计、评估门、变更治理 | **2** |
| 4 | **Degradation & Availability** | 08, 09, 11 | 降级层：失败路径与超时处理 | **4** |
| — | **Input Contract** | 01 | 输入契约：schema gate（跨 1 与 2） | **5** |

**优先级排序**（沿用课程 §3.7 note 行 528 的姿态）：
**Safety / Invariants > Deterministic Authority > Evidence > Selection & Context > Cost / Performance**

**两种失败模式的预防**（note 行 481）：
- *Missing a cluster* → 整个 concern 被遗忘。本项目最易被忘的是 **cluster 3**（Evidence）——
  现在 `REQ-ADS-GOV-001` 只有一个字段清单，无 hook、无评估门、无监控。
- *Mixing unrelated requirements* → 不兼容 tactic 被混为一谈。**cluster 1 需确定性 wrapper，cluster 4 需 timeout + fallback，
  二者结构不同，不可共用一套设计**（不要把超时处理塞进 compliance 管道）。

---

## 6. 风险与假设（A1 阶段暴露）

| ID | 假设 | 若假设错误的影响 | 缓解 + 复审触发 |
|---|---|---|---|
| `R-001` | 无运行时人类复核时，`no_ad` 是充分的安全默认 | 广告不展示虽无害，但若业务要求必须出广告，fail-closed 变为可用性问题 | 明确 `no_ad` 为可接受终态；触发：无广告率 > 阈值 |
| `R-002` | confidence 阈值 0.5 能有效区分可信/不可信 | 阈值过松 → 低质选择被展示；过紧 → 大量降级 | 评估集调参（`REQ-ADS-NFR-QA-001`）；触发：降级率异常 |
| `R-003` | 候选集规模不会超出上下文预算 | 候选过多 → 摘要被裁剪 → LLM 看不到部分候选，选择质量下降 | `ASR-ADS-A3-01` 的 budget monitor；触发：候选数超预算 |
| `R-004` | "解释质量"在广告推荐场景有可定义的口径 | 口径不明 → `ASR-ADS-A3-02` 无法验收，退化为装饰性输出 | **已关闭**：`OQ-009` 于 2026-10-06 确认为「为什么选这条广告」（见 §3.2）；触发：解释评估器无法产出稳定分数 |
| `R-005` | confidence 阈值 0.5 能有效区分可信/不可信 | 阈值过松 → 低质选择被展示；过紧 → 大量降级 | **已定案**：`OQ-004` 于 2026-10-06 关闭，阈值 = 0.5（`config.yaml` 单点控制）；评估集落地后若异常则重开 |

---

## 7. 人工确认清单（Human-in-the-Loop）

按课程 §3.6 规矩（note 行 496）：**AI output = advisory only；Human decision = authoritative。**

| # | 待确认项 | 建议 | 状态 |
|---|---|---|---|
| 1 | 18 ASR / 4 impl 的划分 | 维持；`REQ-ADS-FR-002` 保留为 impl，但需在 `SEC-001` 族下补输入侧校验 | ⏳ 待批 |
| 2 | `REQ-ADS-NFR-PERF-001` 按四元素改写 | 接受（否则踩性能陷阱，性能需求未实现） | ⏳ 待批 |
| 3 | 流程不变量选 3 条：`NFR-QA-002` + `GOV-002` + 失败归因规则 | 接受（课程要求 ≥1 条流程不变量，标注 Required for full marks） | ⏳ 待批 |
| 4 | ~~假设 A-01：「解释」的领域口径~~ | ✅ **已确认**：「为什么选这条广告」（`OQ-009` 于 2026-10-06 关闭） | ✅ 已关闭 |
| 5 | confidence 阈值 | ✅ **已定案** = 0.5（`OQ-004` 于 2026-10-06 关闭） | ✅ 已关闭 |

> 本文件所有"我替你做的判断"均已在正文以 ⭐/⚠️/假设标记显式标出，未静默决定。

---

## 8. 追溯

| 本文件条目 | 上游 | 下游 |
|---|---|---|
| §1 判定表 | `docs/req/requirements.yaml` | `invariants.md`、`trace-matrix.md` |
| §2 结构元素 | `docs/design/technical-design-v1.md`（实现现状） | `architecture-blueprint.md` §4 Components |
| §3 A3 ASR | 课程 §3.3 | `invariants.md`（A3 相关不变量） |
| §5 Cluster | 课程 §3.5 | ADR 候选评估（探索循环） |
| §6 风险 | — | `risk-list.md` |

---

## 9. V2 候选需求的 A1 预判（归属 `docs2/` 轮次，**非正式条目**）

> 状态说明：以下 9 条为**预判**，供 V2 轮次（`docs2/architecture/`）启动时复核。
> 它们**不作为本轮的正式 ASR 条目**，因此不出现在 §2 的统计中，也不被
> `scripts/validate_requirements.py` 的孤儿检查覆盖（候选需求声明 `asr: true` 但暂不填 `asr_id`）。
>
> 预判判据同 §1：litmus ≥ 2 维即为 ASR。

| 来源 REQ（V2） | 需求摘要 | 命中维度 | 预判 | 预判理由 |
|---|---|:-:|---|---|
| `REQ-ADS-ARCH-005` | 预算不变式 `remaining = total − spent` | State + QA + Ev = 3 | **ASR** | 引入跨轮**持久状态**，本 V1 完全没有 State 维度 |
| `REQ-ADS-ARCH-006` | 预算耗尽不得展示 | State + QA = 2 | **ASR** | 强制候选集过滤与状态转换 |
| `REQ-ADS-ARCH-007` | 花费入账精确 | State + Ev = 2 | **ASR** | 强制台账证据与重放能力 |
| `REQ-ADS-NFR-SAFETY-007` | NaN/Inf 必须拦截 | Auth + QA = 2 | **ASR** | 强制数值校验 gate |
| `REQ-ADS-ARCH-010` | 成交价规则唯一 | Auth + Ev = 2 | **ASR** | 强制单一计价路径 |
| `REQ-ADS-ARCH-011` | 平局确定性 tie-break | Auth + QA = 2 | **ASR** | 禁止随机，强制确定性规则 |
| `REQ-ADS-FR-006` | 分数公式单一来源 | Auth + Ev = 2 | **ASR** | 强制配置单一来源 + 变更触发 replay |
| `REQ-ADS-ARCH-012` | LLM 无成交/花费写权限 | Auth + Struct = 2 | **ASR** | schema 层权限边界，V1 的 ARCH-001 之加强 |
| `REQ-ADS-GOV-003` | 竞价规则变更治理 | Auth + Ev + Perm = 3 | **ASR** | permission + hook + replay 门 |

**预判为 implementation 的 10 条**：`REQ-ADS-NFR-SAFETY-006`（出价范围校验）、`REQ-ADS-ARCH-008`（整数分）、
`REQ-ADS-ARCH-009`（评分纯函数）、`REQ-ADS-FR-005`（选出胜者）、`REQ-ADS-FR-007`（转 exhausted）、
`REQ-ADS-FR-008`（快照）、`REQ-ADS-NFR-QA-003`（离线覆盖）、`REQ-ADS-SEC-002`（报价校验）、
`REQ-ADS-NFR-QA-004`（评估用例）、`REQ-ADS-NFR-PERF-002`（计算开销）。

> **V2 轮次启动时必须做的事**：把上述 9 条预判转为正式 ASR-V2-* 条目（**加反引号并填入 `asr_id`**，
> 否则 `scripts/validate_requirements.py` 的孤儿检查会认为它们未被引用），
> 同时把 V1 的 `docs/architecture/` 层标为 **FROZEN / IMMUTABLE**（课程 note 行 106/1531）。
