# 不变量登记册（Invariant Register）

> **A2 产物** · 对应课程 `3. 软件架构.md` §3.2（P15–16）与 §5.4（P55）
> 状态：**草案待人工批准** · 版本：V1 轮次 · 生成日期：2026-10-06
> 输入：`docs/req/requirements.yaml`（RE invariant）+ `docs/architecture/asr-register.md`（A1）
> 下游：`docs/architecture/trace-matrix.md`、`architecture-blueprint.md` §5 Authority
>
> **课程核心论断（note 行 336–342）**：RE invariant 说明**什么绝不能发生**，SA 形式化**如何**：
> 在 RE 的 `statement + fit_criterion` 之外**新增三个字段**——
> **Enforcing Component**（没有它，invariant 只是**愿望**）、
> **Verification**（没有它，invariant **不可审计**）、
> **Fallback**（没有它，invariant 只是**风险/文档**）。

---

## 0. 六个必填字段

| 字段 | 含义 | 来源 |
|---|---|---|
| Invariant ID | 唯一标识 | `INV-ADS-NNN` |
| Statement | **什么绝不能发生**（NEVER，不是 SHOULD） | RE |
| Source Requirement | 追溯到具体 REQ ID | RE |
| Enforcing Component | **具体命名的代码元素**，不是模糊期望 | **SA 新增** |
| Verification Method | 可测试可观测的证明方法（不能只是 "code review"） | **SA 新增** |
| Fallback Action | 即将被违反时的**具体安全动作**，不是"修 bug" | **SA 新增** |

---

## 1. Fail-Closed 方向声明（本项目特有，必须先读）

课程行 1713 给出 fallback 的**方向判据**：

> **Fallback = REVIEW 是 fail-closed；Fallback = retry 是 fail-open；在受监管系统中 fail-closed 是唯一安全默认。**

**本项目没有运行时的人类复核环节**——不存在 VHIS 那样的 `REVIEW` 终态。因此：

| VHIS | 本项目 | 是否等价 |
|---|---|---|
| `REVIEW`（转人工） | **`no_ad`（不展示任何广告）** | ✅ 均为 fail-closed |
| `REVIEW` + checkpoint（人工稍后处理） | 无对应物（无状态、无队列） | ⚠️ 见风险 R-001 |

**`no_ad` 是 fail-closed 的理由**：不展示广告 = 不产生任何合规暴露面 = 安全默认。
系统在不确定时**从不出广告**，而不是出"可能合适的广告"。

### 1.1 一个需要显式说明的例外：重试

`INV-ADS-003`（非法 JSON）含"重试 1 次"。按字面它像 fail-open，实际不是：

> **重试发生在任何展示之前，且重试只是推迟终态，不改变终态。**

无论重试几次，终态都是 `no_ad`；重试期间**没有任何广告被展示**。因此该路径**不构成 fail-open**。
若未来引入"重试后降级到次优候选并展示"，**即变为 fail-open，必须重新走 ADR**（见 §5 重开触发条件）。

### 1.2 审计写入失败的立场（INV-ADS-010）

课程行 538 明确：**audit logging 不可协商（GOV-001），token 节省不能绕过它**。

因此本项目采取：**审计写入失败 → 本次推荐失败（fail-closed），不静默继续。**
理由：无法审计的决策等于无证据决策，违反 `REQ-ADS-GOV-001` 的零容忍条款。
代价：牺牲可用性换取证据完整性——这是**有意的权衡**，记录于 `ADR-002`。

---

## 2. 不变量明细（16 条）

### 2.1 安全类不变量（safety invariants）

---

**`INV-ADS-015`** — 素材契约：schema 不合法绝不进入系统

| 字段 | 内容 |
|---|---|
| Statement | **任何不满足素材 schema 的记录绝不得进入候选集或任何决策路径。** |
| Source Requirement | `REQ-ADS-ARCH-001`（对应 A1 的 `ASR-ADS-01`） |
| Enforcing Component | `ads.schema.AD_SCHEMA` + `ads.repository.AdRepository.load()`（加载期逐条校验） |
| Verification Method | 反例测试：缺必填字段、设备枚举越界、`ad_id` 格式错误、重复 `ad_id` 各 1 例；断言**加载整体失败并指明第几条**（不跳过单条） |
| Fallback Action | **拒绝整批加载并报错（fail-closed）**，阻断服务启动直至素材修复 |

---

**`INV-ADS-001`** — 未经确定性合规过滤的广告绝不被展示

| 字段 | 内容 |
|---|---|
| Statement | **任何广告在展示前必须通过确定性合规过滤；不存在任何绕过路径。** |
| Source Requirement | `REQ-ADS-NFR-SAFETY-001`（对应 A1 的 `ASR-ADS-04`） |
| Enforcing Component | `compliance.pipeline.run_compliance()`（**五步**纯函数管道：`check_output` → `check_banned_words` → `check_banned_check` → `check_category` → `check_scene`） |
| Verification Method | 单元测试：全部规则分支各 1 反例（违禁词/品类/夜间/校园/设备/集外 ID）；管道任一失败 → `approved=False`。对抗测试：构造绕过尝试，**逃逸数必须为 0** |
| Fallback Action | **REJECT → 降级 `no_ad`**（原因码 `compliance_rejected` + 失败规则名），并写审计告警 |

---

**`INV-ADS-002`** — AI 绝不在候选集之外选择

| 字段 | 内容 |
|---|---|
| Statement | **LLM 返回的 `ad_id` 绝不出现在候选集之外。** |
| Source Requirement | `REQ-ADS-ARCH-002`（`ASR-ADS-02`） |
| Enforcing Component | `ads.repository.AdRepository.filter_by_scene()`（构造候选集）+ `compliance.pipeline.check_output()`（存在性 gate） |
| Verification Method | 反例测试：注入候选集外 `ad_id`，断言被 REJECT；**已展示的集外广告数 = 0** |
| Fallback Action | **REJECT → 降级 `no_ad`**（原因码 `output_not_in_candidates`） |

---

**`INV-ADS-003`** — 非法 LLM 输出绝不进入决策

| 字段 | 内容 |
|---|---|
| Statement | **不符合输出 schema 的 LLM 输出绝不被当作有效选择。** |
| Source Requirement | `REQ-ADS-ARCH-003`（`ASR-ADS-03`） |
| Enforcing Component | `selector.parser.parse_llm_output()`（严格 JSON 解析 + schema 校验） |
| Verification Method | 畸形 JSON 语料测试：缺字段、类型错、多余字段、非 JSON 文本——**零次进入决策** |
| Fallback Action | **重试 1 次 → 仍失败 → 降级 `no_ad`**（原因码 `llm_output_invalid`）。重试期间不展示任何广告（见 §1.1） |

---

**`INV-ADS-004`** — 解释路径绝不影响决策

| 字段 | 内容 |
|---|---|
| Statement | **解释（`reason`）路径绝不得改写决策结果，也绝不得绕过合规 gate。** |
| Source Requirement | `ASR-ADS-A3-02`（A3 新增；对应课程 INV-004） |
| Enforcing Component | 解释输出组装元素（决策路径与解释路径**结构分离**；解释无法访问 `ad_id` 写入口） |
| Verification Method | 隔离测试：注入"解释评估失败"与"解释含违禁词"，断言 **`ad_id` 不变**且解释被剥离；解释内容经 `check_banned_words` 复查 |
| Fallback Action | **只降级解释**（返回结构化摘要），`ad_id` 保持不变；若解释含违禁词则**丢弃解释文本**并写审计 |

---

**`INV-ADS-005`** — 注入模式绝不抵达模型

| 字段 | 内容 |
|---|---|
| Statement | **已知注入模式绝不在未中和的情况下抵达 LLM。** |
| Source Requirement | `REQ-ADS-SEC-001`（`ASR-ADS-12`；对应课程 INV-005） |
| Enforcing Component | 输入 sanitize gate（pipeline **第一级**，位于任何模型调用之前）+ `selector.parser.parse_llm_output()`（输出侧第二层） |
| Verification Method | 对抗回归集：中文与英文注入样本；断言**中和率 100%**、被当作指令执行的样本数 = 0 |
| Fallback Action | **拦截该请求 → 降级 `no_ad`**（原因码 `injection_detected`），记录原始输入供回归 |

---

**`INV-ADS-006`** — 低置信度绝不被当作可信

| 字段 | 内容 |
|---|---|
| Statement | **`confidence` 低于阈值的 LLM 输出绝不被采纳为展示依据。** |
| Source Requirement | `REQ-ADS-NFR-SAFETY-005`（`ASR-ADS-08`） |
| Enforcing Component | 阈值 gate（`config.yaml` 的 `selector.confidence_threshold`，单点定义，当前 0.5） |
| Verification Method | 反例测试：边界值 `threshold-1` / `threshold` / `threshold+1` 三档；断言**低于阈值的展示数 = 0** |
| Fallback Action | **降级 `no_ad`**（原因码 `low_confidence`），记录原始 `confidence` 值 |

---

**`INV-ADS-007`** — 敏感品类与违禁词绝不展示

| 字段 | 内容 |
|---|---|
| Statement | **黑名单品类与含违禁词的广告绝不被展示。** |
| Source Requirement | `REQ-ADS-NFR-SAFETY-002` + `REQ-ADS-NFR-SAFETY-003`（`ASR-ADS-05`、`ASR-ADS-06`） |
| Enforcing Component | `compliance.pipeline.check_category()` + `check_banned_words()`（**两个独立 gate，便于单独审计**）+ `compliance.rules.SceneRules.category_blacklist` |
| Verification Method | 反例测试：金融承诺 / 成人 / 医疗品类各 1 例；违禁词命中 `title` 与 `copy` 各 1 例；断言**展示数 = 0** |
| Fallback Action | **REJECT → 降级 `no_ad`**；命中词/品类写入审计，用于词表迭代 |

---

**`INV-ADS-008`** — 场景约束绝不违反（双层）

| 字段 | 内容 |
|---|---|
| Statement | **违反广告自身声明或规则级场景禁忌的广告绝不被展示。** |
| Source Requirement | `REQ-ADS-NFR-SAFETY-004`（`ASR-ADS-07`） |
| Enforcing Component | **第一层**：`AdRepository.filter_by_scene()`（候选集构建时剔除）；**第二层**：`compliance.pipeline.check_scene()`（展示前终检） |
| Verification Method | 反例测试：夜间 + gaming、校园 + adult、设备不符三类；断言**违规展示数 = 0**；双层各自独立测试 |
| Fallback Action | **REJECT → 降级 `no_ad`**（原因码 `scene_violation` + 具体冲突项） |

---

### 2.2 流程类不变量（process invariants，3 条）

> 课程明确要求不变量登记册含**至少 1 条流程不变量**（行 5143），且标注 **Required for full marks**（行 5122）。
> 流程不变量管的是**工作流行为**，不只是数值限额。本项目设 3 条。

---

**`INV-ADS-009`** — 失败归因：绝不静默 patch 代替架构修订 ⭐

| 字段 | 内容 |
|---|---|
| Statement | **当 agent 遵守了全部约束、结构测试通过、但行为/质量测试失败时，绝不得直接修改 safety-critical 代码；必须先产出架构修订记录（ADR + 工件更新）。** |
| Source Requirement | `REQ-ADS-GOV-002` + `ASR-ADS-A3-03`（课程 §10.1 note 行 4229：**The code is CORRECT. The architecture is UNDERSPECIFIED.**） |
| Enforcing Component | `pre_write_hook()`（拦截 safety-critical 文件的无 ADR 变更）+ CI 检查（提交含 safety-critical 路径变更时要求 ADR 存在） |
| Verification Method | 模拟测试：构造"测试失败 → 直接改 safety-critical 文件、无 ADR"的提交，断言**被阻断**；断言 safety-critical 文件的未记录变更数 = 0 |
| Fallback Action | **阻断写入（fail-closed）**，要求补 ADD-R 记录（delta specification）后方可继续 |

---

**`INV-ADS-010`** — 改 safety-critical 文件须有权限与 hook 双重强制

| 字段 | 内容 |
|---|---|
| Statement | **safety-critical 路径的变更绝不得在缺少权限声明或事件钩子的情况下进入仓库。** |
| Source Requirement | `REQ-ADS-GOV-002`（`ASR-ADS-13`；对应课程 GOV-002） |
| Enforcing Component | **Permission Model**（`.opencode/permissions.jsonc` 声明谁可写哪些路径）**AND** **pre-commit hook**（变更时事件触发拦截）。二者互补：**Permission 定义 WHO，Hook 强制 WHEN** |
| Verification Method | 权限矩阵测试（每个角色对每条路径的读写被实际拒绝/允许）；hook 模拟测试（无 ADR 的 safety-critical 变更被拦截） |
| Fallback Action | **拒绝该次写入**；违反记录进 `debt-register.md` 并要求人工评审 |

---

**`INV-ADS-011`** — 验证完整性：每条 fit criterion 有测试，每条不变量有失败测试 ⭐

| 字段 | 内容 |
|---|---|
| Statement | **任何 fit criterion 绝不得在无测试的情况下进入基线；任何不变量绝不得只有通过测试而没有会失败的测试。** |
| Source Requirement | `REQ-ADS-NFR-QA-002`（`ASR-ADS-16`） |
| Enforcing Component | `test/offline` 测试套件 + 覆盖面校验（fit criterion ↔ 测试映射）+ CI 门 |
| Verification Method | 遍历 `requirements.yaml` 全部 fit criterion，断言每条至少 1 个测试引用；对每条不变量执行**变异验证**：注入违规后失败测试**确实失败** |
| Fallback Action | **阻断合并（fail-closed）**；缺口登记进 `debt-register.md`，不得静默通过 |

---

### 2.3 证据与可用类不变量

---

**`INV-ADS-012`** — 每次请求恰好 1 条完整审计证据

| 字段 | 内容 |
|---|---|
| Statement | **每次推荐请求绝不得产生 0 条或 2 条以上审计记录；证据字段绝不得缺失。** |
| Source Requirement | `REQ-ADS-GOV-001`（`ASR-ADS-10`） |
| Enforcing Component | `audit` 模块（JSONL 追加写，请求生命周期内恰好一次写入） |
| Verification Method | 计数断言：**每次请求恰好 1 条**（含异常路径）；字段完整性断言：场景、候选集规模、LLM 原始输出、过滤结果、最终输出、模型与 prompt 版本全部非空 |
| Fallback Action | **本次推荐失败（fail-closed）**，不得静默继续（立场见 §1.2）；写审计告警 |

---

**`INV-ADS-013`** — 超时与失败绝不导致崩溃或未处理异常

| 字段 | 内容 |
|---|---|
| Statement | **LLM 超时、API 异常、候选集为空等失败绝不得导致进程崩溃或抛出未处理异常。** |
| Source Requirement | `REQ-ADS-FR-003` + `REQ-ADS-NFR-PERF-001`（`ASR-ADS-09`、`ASR-ADS-11`） |
| Enforcing Component | **timeout gate**（LLM 调用超时控制，`config.yaml` 的 `timeout_sec`）+ **fallback path**（异常 → `no_ad`）+ **p95 延迟监控** + **SLA drift alert** |
| Verification Method | 离线模拟：LLM 超时、抛异常、候选集为空、p95 超阈值各 1 例；断言**进程正常退出且返回结构化 `no_ad`**；监控指标可观测 |
| Fallback Action | **降级 `no_ad`**（原因码区分：`llm_timeout` / `llm_error` / `no_candidates` / `latency_sla_breach`）；触发 drift alert 供人工介入 |

---

**`INV-ADS-014`** — 上下文预算绝不被突破，关键约束绝不因压缩而消失

| 字段 | 内容 |
|---|---|
| Statement | **单次推荐的上下文 token 绝不得超过配置上限；standing constraints 绝不得因 compaction 而丢失。** |
| Source Requirement | `REQ-ADS-NFR-COST-001`（`ASR-ADS-14`、`ASR-ADS-A3-01`） |
| Enforcing Component | `route_budget()`（三档路由：DIRECT / SUMMARIZE / REVIEW）+ token counter + summarization gate + **re-injection 机制**（compaction 后重新注入层 2 约束） |
| Verification Method | 单元测试：三档路由边界；**re-injection 断言——compaction 后 standing constraints 仍在最终 prompt 中**；超预算请求被截断并记录 |
| Fallback Action | **降级为 SUMMARIZE 路径**；若仍超上限 → **`no_ad`**（原因码 `budget_exceeded`），记录 token 计数 |

---

**`INV-ADS-016`** — 语义评估门禁：质量回退绝不静默进入产物

| 字段 | 内容 |
|---|---|
| Statement | **固定评估集上的质量阈值绝不可以在未通过的情况下让变更进入产物。** |
| Source Requirement | `REQ-ADS-NFR-QA-001`（`ASR-ADS-15`） |
| Enforcing Component | `eval.eval_runner`（CI 阻断门）+ `eval/eval_cases.json`（固定评估集，≥20 条） |
| Verification Method | replay 断言：评估集 ≥ 20 条且可一键运行；阈值失败时 CI **阻断合并**并输出通过率与违规数 |
| Fallback Action | **阻断合并（fail-closed）**，报告失败用例与违规数；变更不得进入产物 |

---

## 2.4 覆盖表（需求 ↔ 不变量）

> 说明：一条不变量可服务多条需求（例如商品/违禁词两类 gate 同由 `INV-ADS-007` 覆盖）。
> 本表使「哪条需求由哪条不变量保护」可查，并暴露无保护的需求。

| 需求 | 不变量 | 备注 |
|---|---|---|
| `REQ-ADS-ARCH-001` | `INV-ADS-015` | 素材契约 |
| `REQ-ADS-ARCH-002` | `INV-ADS-002` | 闭集选择 |
| `REQ-ADS-ARCH-003` | `INV-ADS-003` | 输出 JSON |
| `REQ-ADS-ARCH-004` | — | 可复现性，判为 implementation（无独立不变量） |
| `REQ-ADS-NFR-SAFETY-001` | `INV-ADS-001` | 零逃逸（核心） |
| `REQ-ADS-NFR-SAFETY-002` | `INV-ADS-007` | 与 SAFETY-003 共享 |
| `REQ-ADS-NFR-SAFETY-003` | `INV-ADS-007` | 与 SAFETY-002 共享 |
| `REQ-ADS-NFR-SAFETY-004` | `INV-ADS-008` | 场景双层 |
| `REQ-ADS-NFR-SAFETY-005` | `INV-ADS-006` | 置信度 |
| `REQ-ADS-FR-003` | `INV-ADS-013` | 降级不崩溃 |
| `REQ-ADS-NFR-PERF-001` | `INV-ADS-013` | 与 FR-003 共享 |
| `REQ-ADS-SEC-001` | `INV-ADS-005` | 注入 |
| `REQ-ADS-NFR-COST-001` | `INV-ADS-014` | 预算与压缩 |
| `REQ-ADS-NFR-QA-001` | `INV-ADS-016` | 评估门 |
| `REQ-ADS-NFR-QA-002` | `INV-ADS-011` | 验证完整性（流程） |
| `REQ-ADS-GOV-001` | `INV-ADS-012` | 审计证据 |
| `REQ-ADS-GOV-002` | `INV-ADS-009`、`INV-ADS-010` | 流程不变量 |
| `REQ-ADS-AI-001` | `INV-ADS-004` | 解释路径隔离 |
| `REQ-ADS-AI-002` | `INV-ADS-009`、`INV-ADS-012` | 与 GOV 共享 |
| `REQ-ADS-FR-001`、`FR-002`、`FR-004` | — | 判为 implementation，不变量不适用 |


---

## 3. 自查（课程 §5.11 "What Makes a Good Invariant Entry?"，note 行 1693）

| 自查项 | 本项目情况 |
|---|---|
| Statement 是否说明什么必须 **NEVER** 发生（而非 SHOULD）？ | ✅ 16 条全部以"绝不"表述 |
| Enforcing Component 是否为**具体命名代码元素**？ | ✅ 全部指向具体模块/函数（如 `compliance.pipeline.run_compliance()`） |
| Verification 是否可测试可观测（不只是 "code review"）？ | ✅ 全部含具体测试方法或边界值 |
| Fallback 是否为**具体安全动作**？ | ✅ 全部为 `no_ad` / 阻断加载 / 阻断合并 / 降级解释，无一写成"修 bug" |
| Source REQ 是否追溯到具体需求 ID？ | ✅ 全部追溯到 `REQ-ADS-*` |
| 是否处于**不同层级**（safety / structural / governance）？ | ✅ 安全 9 条 + 流程 3 条 + 证据可用 4 条 |
| 至少 **3 条**？ | ✅ 16 条 |
| 至少 **1 条流程不变量**？ | ✅ 3 条（`INV-ADS-009` / `010` / `011`） |

**统计：16 条不变量**（安全 9 + 流程 3 + 证据可用 4）。

---

## 4. 风险

| ID | 假设 | 若错误的影响 | 缓解 + 复审触发 |
|---|---|---|---|
| `R-001` | `no_ad` 是充分的安全默认 | 若业务要求"必须出广告"，fail-closed 转为可用性缺陷 | 明确 `no_ad` 为可接受终态；触发：无广告率超阈值 |
| `R-005` | 审计写入失败时应当整体失败（§1.2 立场） | 存储故障时推荐服务完全不可用 | 区别于"审计可延迟"的替代方案；触发：审计写入失败率 > 阈值 → 重开 `ADR-002` |
| `R-006` | 输入侧只有场景特征，注入面较小 | 若未来引入自由文本输入，`INV-ADS-005` 的 sanitize gate 强度不足 | 新增自由文本输入即触发重开 `ADR-001` |

---

## 5. 重开触发条件（Re-open Triggers）

任一条成立时，本登记册必须修订并走 ADR：

| 触发 | 影响的不变量 |
|---|---|
| 引入"重试后展示次优候选"（fail-open） | `INV-ADS-003` |
| 引入运行时人类复核环节 | §1 的 `no_ad` 映射（可能改为 `REVIEW`） |
| 引入自由文本用户输入 | `INV-ADS-005` |
| 引入多轮上下文/记忆 | `INV-ADS-014`（层 4 HISTORY 由"不适用"变为适用） |
| 审计存储改为异步/可延迟 | `INV-ADS-012` |
| compliance 任一 gate 规则变更 | `INV-ADS-001`、`007`、`008` |

---

## 6. 人工确认清单

| # | 待确认项 | 建议 | 状态 |
|---|---|---|---|
| 1 | 16 条不变量是否合适（是否过多/过少） | 覆盖全部 safety 与流程门；建议维持 | ⏳ 待批 |
| 2 | `no_ad` 作为 fail-closed 终态是否被团队接受 | 接受（本项目无人类复核环节） | ⏳ 待批 |
| 3 | §1.2 审计失败即整体失败的立场 | 接受（课程：audit 不可协商） | ⏳ 待批 |
| 4 | `INV-ADS-004` 的"解释"口径 | ✅ **已确认**：「为什么选这条广告」（`OQ-009` 于 2026-10-06 关闭，见 `asr-register.md` §3.2） | ✅ 已关闭 |

> 本文件所有判断均已显式标注，未静默决定。
