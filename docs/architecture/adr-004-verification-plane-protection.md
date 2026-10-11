# ADR-004：评估与验证资产纳入受保护路径清单（ADR-002 D4 的补充）

> 课程对应：note 行 3916–3926（评估门）、行 5138–5142（Capstone ADR 评分量规）、
> D3 的 `.agent/rules.md` 关于"safety-critical 变更须架构决策与人工批准"的公约要求
> **状态**：**Accepted（已批准）** · 批准日期：**2026-10-06** · 批准者：**Shane**（具名人类）
> **日期**：2026-10-06 · **决策负责人**：D（质量与治理）+ A（产品与流程）
>
> **依赖**：`ADR-002`（本 ADR **补充**其 §2 D4 的受保护路径清单）、
> `ADR-003`（评估集为一等架构资产 —— 本 ADR 为其提供强制机制）
>
> **性质**：这是一份 **`ADR-002` 的修订型补充（amendment）**，不是取代。
> 按 `ADR-002` 的**冻结语义**（其状态为 `Accepted` 后进入只读），
> 新增受保护路径**不得直接改写 ADR-002 的表**，故以本 ADR 承载补充清单。
> `ADR-002` 原文中仅新增一个 `<!-- safety-critical-paths -->` 标记（供检查器定位其清单），
> **其路径表内容一字未改**。
>
> **批准记录**：人类于 2026-10-06 在三个方案中选择「甲 —— 新建 ADR-004」。
> **No agent may self-approve**（课程 §11.3）—— 本次决策由人类做出，agent 仅起草。
> **冻结语义**：`Accepted` 后本 ADR 进入只读；后续变更须再新增修订型 ADR。

---

## 1. Context

### 1.1 问题（`TD-025`）

`ADR-003` 确立了评估集为**一等架构资产**，`INV-ADS-016` 要求"评估门：阈值失败必须阻断"。
但 `ADR-002` §2 D4 的受保护路径清单**未包含** `eval/`。后果是：

> **删掉难例，或把 `expected_ad_id` 改宽，即可在不改实现的情况下让门禁 4 变绿。**

这是一个**典型的治理漏洞**：门禁在形式上"生效"（脚本运行、报告输出、退出码正确），
实质上被绕过 —— 因为**判据本身可被随意改动**。

### 1.2 为什么这属于"必须修"而非"可以接受"

本项目在 `.agent/rules.md` 的 **R2** 中已把"为通过检查而改变判据"列为**最严重违规**，
理由写在规则里：

> 因为它是**掩盖而非失败**。

但在 `TD-025` 登记时，**规则被写下了、锁却没有装上** ——
机器无法阻止改 `eval/eval_cases.json`。**规则与机制不一致**。

课程要求 **Permission 定义 WHO，Hook 强制 WHEN**（note 行 599）。
`ADR-002` D4 正是"Permission"的机器可读形式；`eval/` 不在其中，等于**声明了却未强制**。

### 1.3 同类风险的完整清点（不止 `eval/`）

`TD-025` 只提到 `eval/`，但审查后发现**同一漏洞模式**还波及另外三类资产：

| 资产 | 若被削弱，会怎样 | 原受保护状态 |
|---|---|---|
| `eval/eval_cases.json` | 删难例让门禁 4 变绿 | ❌ 未保护 |
| `eval/eval_runner.py` | 改判定逻辑（如恒返回 passed） | ❌ 未保护 |
| `scripts/fitness_functions.py` | 削弱 S1–S3、V1–V4 的检查 | ❌ 未保护 |
| `scripts/mutation_check.py` | 删掉变异、或让 `_classify` 恒判"已检出" | ❌ 未保护 |
| `scripts/check_*.py`（六道门禁检查器） | 直接让门禁恒通过 | ❌ 未保护 |
| `docs/code-governance/acceptance-coverage-map.yaml` | 把 `test_backed` 改 true 而无证据 | ❌ 未保护 |

**这六类合起来构成"验证平面"（verification plane）** —— 它们不参与运行时决策，
但**决定"什么算正确"**。若验证平面可被被测方随意改动，则全部门禁都失去意义。

### 1.4 约束

- 本 ADR **不得**改写 `ADR-002` 的路径表（冻结语义）。
- 检查器 `scripts/check_safety_paths.py` 原先**只读 `ADR-002`** 一个文件 ——
  须扩展为支持多份 ADR 的清单合并（**用显式标记**，不做全表扫描 —— 见 §2 D4）。
- 受保护不等于"不可改"：它意味着**改动须附架构决策并经人工批准**。正常演进仍可进行。

---

## 2. Decision

### D1 — 建立"验证平面"概念，并把它的六类资产纳入受保护清单

新增受保护路径（与 `ADR-002` D4 的同级条目合并生效）：

<!-- safety-critical-paths -->

| 路径 | Plan Agent | Build Agent | 人工必须？ |
|---|---|---|---|
| `eval/eval_cases.json` | Read | Read | **是 — 须 ADR** |
| `eval/eval_runner.py` | Read | Read | **是 — 须 ADR** |
| `scripts/fitness_functions.py` | Read | Read | **是 — 须 ADR** |
| `scripts/mutation_check.py` | Read | Read | **是 — 须 ADR** |
| `scripts/check_test_approval.py` | Read | Read | **是 — 须 ADR** |
| `scripts/check_ai_use_log.py` | Read | Read | **是 — 须 ADR** |
| `scripts/check_semantic_eval.py` | Read | Read | **是 — 须 ADR** |
| `scripts/check_safety_paths.py` | Read | Read | **是 — 须 ADR** |
| `scripts/check_dependencies.py` | Read | Read | **是 — 须 ADR** |
| `docs/code-governance/acceptance-coverage-map.yaml` | Read/Write | Read | **是 — 须 ADR** |

改动其中任一，提交须**附带 ADR 引用**，否则 CI **阻断**（`check_safety_paths.py`）。

> **为什么 Build Agent 是 `Read` 而非 `No access`**：验证资产需要被**运行与调试**
> （BUILD 要跑 `eval_runner` 看自己是否达标）。故给读权限、不给"无 ADR 写"权限。
> 这与 `src/compliance/`（Build = No access）的区别是：
> 合规层的**存在本身就是保证**，而验证资产的**运行**是保证的一半。

### D2 — 验证平面的定义（供后续判断新资产是否属于它）

一条资产属于**验证平面**，当且仅当它满足：

> **它决定"什么算正确"，而不是决定"系统做什么"。**

运行平面（runtime plane）：`src/**` —— 决定系统行为。
验证平面（verification plane）：`eval/**`、`scripts/**`、`data/*.json`、
`docs/code-governance/**`、`docs/architecture/**` —— 决定**判据**。

**两平面不得由同一方可无约束地改动。** 这是本 ADR 的核心原则。

### D3 — 新增受保护路径的**流程**

今后新增受保护路径，须：

1. 新建一份 ADR（**不得改写已 Accepted 的 ADR 的表**）；
2. 在该 ADR 中放入 `<!-- safety-critical-paths -->` 标记，紧随其后放路径表；
3. 检查器自动合并（见 D4），无需改代码。

### D4 — 检查器改为**标记驱动**的多 ADR 合并

`scripts/check_safety_paths.py` 原实现**硬编码只读 `ADR-002`**。现改为：

- 扫描 `docs/architecture/adr-*.md`；
- 识别其中的 `<!-- safety-critical-paths -->` 标记；
- 解析**标记之后的第一张表**，合并全部 ADR 的清单。

**刻意使用显式标记，而非"扫描所有表格"**：其它 ADR 的表格
（如"备选方案对比""重开触发器"）也会出现路径字符串，
无差别解析会把它们**误当成受保护路径**，造成假拦截。
标记使"哪张表是清单"成为一个**显式声明**，而非解析器的猜测。

### D5 — 本 ADR 不追溯既往

`eval/` 与 `scripts/` 中在此 ADR **之前**产生的变更不受本约束（那些变更已经被记录在
`docs/ai-use-log.yaml` 与 `docs/plans/` 中）。本 ADR **自批准之日起前向生效**。

---

## 3. Rationale

| 决定 | 理由 |
|---|---|
| D1 纳入验证平面 | 否则 `.agent/rules.md` 的 R2（不得改判据）**只有文字、没有锁** —— 规则与机制不一致 |
| D1 覆盖不止 `eval/` | 审查发现同一漏洞模式波及六类资产；只修 `eval/` 会留下其余五个同样的洞 |
| D1 Build = Read | 验证资产需被运行调试；给读权限使 BUILD 能自检，同时封住"无 ADR 写" |
| D2 提出两平面原则 | 使新资产是否属于验证平面**可判断**，而非逐案争论 |
| D3 流程化 | 新增路径不必改代码；且**不必改写已冻结的 ADR** |
| D4 标记驱动 | 显式声明胜过解析器猜测；避免误解析无关表格造成假拦截 |
| D5 不追溯 | 与 `ADR-002` D4、`TD-018`/`TD-021` 的历史缺口处理一致 —— **缺口登记而非追溯伪造** |

---

## 4. Alternatives

| 备选 | 为何未采纳 |
|---|---|
| **不改，`TD-025` 保持开放** | 门禁 4 可被一行 JSON 编辑绕过；且 R2 已成空文 |
| **改写 `ADR-002` D4 的表** | 违反 `ADR-002` 自己的冻结语义；开"直接改 Accepted ADR"的先例，削弱全部 ADR 的可信度 |
| **只保护 `eval_cases.json`** | 漏掉 `eval_runner.py`（可改判定逻辑）与 `scripts/`（可让门禁恒通过）—— 只堵一个洞 |
| **把验证平面整体设为 Build = No access** | 会使 BUILD 无法运行/调试评估与检查器，实际降低可用性；且"读"不构成治理风险 |
| **检查器全局扫描所有 ADR 表格** | 会误解析其它语义的表格（备选方案、重开触发器），造成假拦截 —— 假拦截与假放行同样有害 |
| **要求每次改动验证平面都新建 ADR 文件** | 过重：小的措辞修正也要新 ADR。折中为"**引用**已有 ADR ID 即可"（检查器已支持） |

---

## 5. Consequences

**收益（+）**

- `TD-025` 的漏洞被堵上：**改动评估集或检查器现在须附架构决策**，否则 CI 阻断。
- `.agent/rules.md` 的 R2（不得改判据）**从文字变成机制** —— 规则与强制一致。
- **"验证平面"成为显式概念**，使后续判断有据可依（D2），而非逐案争论。
- 检查器支持多 ADR 合并，**新受保护路径无需改代码**（D3），降低了未来的治理成本。

**代价（−）**

- **治理摩擦上升**：今后微调 `eval_cases.json` 的期望值也须引用 ADR。
  这是**刻意的** —— 该文件的性质就是判据，不是普通数据。
- 检查器的行为依赖 `<!-- safety-critical-paths -->` 标记：
  若有人在新增 ADR 时**忘放标记**，清单不会生效（静默失败）。
  缓解：`--show-paths` 会打印**清单来源的 ADR 文件名**，忘放标记在审查中可见。
- 受保护路径清单从 9 条增至 19 条，`check_safety_paths.py` 的阻断面扩大。

**引入的新债**

- `TD-028`：清单"忘放标记"是**静默失败**，目前无机械检查。
  补法：让 `fitness_functions.py` 断言"每份含路径表的 ADR 都带标记"。

---

## 6. Re-open Triggers

| # | 触发条件 | 必须动作 |
|---|---|---|
| **T1** | 新增第七类验证资产，而 D2 的判据无法明确归类它 | 重开本 ADR，细化 D2 |
| **T2** | 出现"漏放标记导致清单未生效"的实例 | 立即执行 `TD-028` 的补法（机械检查标记） |
| **T3** | 受保护清单导致正常演进被阻断 ≥ 3 次 | 复审清单粒度（可能应收紧到"仅评据与检查器"，而非全部脚本） |
| **T4** | `ADR-002` 因其它原因被修订 | 届时可将本 ADR 的清单**合并回** `ADR-002`，本 ADR 标记为 superseded |

---

## 7. Related Requirements

**承载需求**：`REQ-ADS-GOV-002`（权限模型 + hook）、`REQ-ADS-NFR-QA-002`（验证完整性）。

**相关不变量**：`INV-ADS-010`（safety-critical 变更须 ADR + 人工批准 —— 本 ADR 的直接依据）、
`INV-ADS-011`（测试须具备证伪能力 —— 变异验证受本 ADR 保护）、
`INV-ADS-016`（评估门 —— 其判据受本 ADR 保护）。

**相关 ADR**：`ADR-002`（本 ADR 补充其 D4）、`ADR-003`（评估集为一等架构资产 —— 本 ADR 为其上锁）。

**已解决的待决项**：无（`TD-025` 是债不是 OQ）。

---

## 8. Related Artifacts

| 工件 | 关系 |
|---|---|
| `docs/debt-register.md` 的 `TD-025` | 本 ADR 关闭该条目；新增 `TD-028` |
| `scripts/check_safety_paths.py` | 本 ADR D4 的落地（标记驱动的多 ADR 合并） |
| `docs/architecture/adr-002-*.md` §2 D4 | 仅新增标记，路径表未改 |
| `docs/code-governance/mcp-tool-manifest.md` §3 | 路径授权表须同步体现新增保护 |
| `.opencode/permissions.jsonc` 的 P-009 | 原标 `eval/` 为 `unprotected`、指向 `TD-025` —— 须更新为 `safety_critical` |
| `.agent/rules.md` §5.1 | 上下文新鲜度清单 —— 本 ADR 属须同步项 |
| `docs/ai-use-log.yaml` | 门禁 6：本次变更须记录 |
