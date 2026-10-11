# 运行时策略目录（Runtime Policy Catalog）

> 课程对应：note 行 1506–1514（P64）。行业名称包括 runbook（SRE）、playbook（incident response）、FMEA（safety-critical）。
> **规则**：每条失败模式都要有既定策略，**无歧义**；**每条降级路径都必须映射到响应**。
> **状态**：草案待批 · 版本：V1（`docs/architecture/` 轮次）· 日期：2026-10-06
> **上游**：`adr-002-fail-closed-and-governance.md`（fail-closed 终态）、`docs/architecture/invariants.md`

---

## 0. 必填字段

| 字段 | 含义 |
|---|---|
| Policy ID + Trigger | 策略编号与**可观测**的触发条件 |
| System Action | 系统实际做什么（确定性动作，非"调查一下"） |
| Evidence captured | 落进审计证据的内容 |
| Escalation condition | 什么情况下升级到人工 |
| Related invariant | 受哪条不变量约束 |

**本项目降级终态统一为 `no_ad`**（见 ADR-002 D1）。下表所有 fallback 均为 fail-closed。

---

## 1. 策略表

### 输入与契约类

---

**`RP-001` — 素材契约违规**

| 字段 | 内容 |
|---|---|
| **Trigger** | 素材文件缺失 / 非法 JSON / 顶层非数组 / 某条不满足 `AD_SCHEMA` / `ad_id` 重复 |
| **System Action** | **拒绝整批加载并报错**（`AdLoadError`，指明第几条）；**不跳过单条、不降级**；**阻断服务启动** |
| **Evidence captured** | 文件路径、失败条目序号、schema 校验失败信息（`e.message`） |
| **Escalation condition** | 生产环境出现即**立即升级人工**（数据完整性事故）；`load_failure_count > 0` |
| **Related invariant** | `INV-ADS-015`、`REQ-ADS-ARCH-001` |

> 与课程 VHIS `RP-00x` 的差别：VHIS 可在运行时降级为 `REVIEW`；本项目素材是**启动期契约**，
> 因此策略是**启动失败（fail-closed）**而非运行期降级。

---

**`RP-002` — 场景输入非法**

| 字段 | 内容 |
|---|---|
| **Trigger** | 场景输入非对象 / 缺字段 / 枚举越界 / 多余字段 |
| **System Action** | **拒绝该请求**（`SceneInputError`）；**不进入 LLM**（省 token 且缩小攻击面）；返回明确原因 |
| **Evidence captured** | 原始输入、`jsonschema` 校验失败信息、请求时间 |
| **Escalation condition** | 非法输入率 > 阈值（可能为探测性攻击）；连续出现同类越界枚举 → 检查上游调用方 |
| **Related invariant** | `REQ-ADS-FR-002`（implementation 级，但仍需 fail-closed） |

---

**`RP-003` — 注入模式检出**

| 字段 | 内容 |
|---|---|
| **Trigger** | 输入 sanitize gate 命中已知注入模式 |
| **System Action** | **拦截该请求 → `no_ad`**（原因码 `injection_detected`）；原始输入**不送达 LLM**；记录原始样本供回归 |
| **Evidence captured** | 原始输入（脱敏后）、命中的模式 ID、时间戳 |
| **Escalation condition** | 任一次检出即触发 prompt 复核（课程：any occurrence → prompt review）；检出率上升 → 扩充对抗回归集 |
| **Related invariant** | `INV-ADS-005`、`REQ-ADS-SEC-001` |

---

### AI 输出类

---

**`RP-004` — LLM 输出非法 JSON / schema 不符**

| 字段 | 内容 |
|---|---|
| **Trigger** | `parse_llm_output()` 解析失败，或字段类型/取值违反输出 schema |
| **System Action** | **重试 1 次 → 仍失败 → `no_ad`**（原因码 `llm_output_invalid`） |
| **Evidence captured** | LLM 原始输出全文、解析异常信息、重试次数、模型与 prompt 版本 |
| **Escalation condition** | 畸形输出率 > 5% → 检查 prompt 与供应商；连续失败 → 进入 `RP-010` 评估失败流程 |
| **Related invariant** | `INV-ADS-003`、`REQ-ADS-ARCH-003` |

> **fail-open 说明**（课程行 1713）：重试**不是** fail-open，因为重试发生在任何展示之前，
> 且不改变终态（终态仍为 `no_ad`），重试期间无广告被展示。见 `invariants.md` §1.1。

---

**`RP-005` — LLM 选择候选集外的 `ad_id`**

| 字段 | 内容 |
|---|---|
| **Trigger** | 返回的 `ad_id` 不在候选集内 |
| **System Action** | **REJECT 该输出 → `no_ad`**（原因码 `output_not_in_candidates`）；**不尝试"纠正"为最接近的候选** |
| **Evidence captured** | 返回的 `ad_id`、候选集 ID 列表、原始 LLM 输出 |
| **Escalation condition** | 任一次发生即升级（说明 LLM 未遵守闭集约束 → 检查 prompt 与模型版本） |
| **Related invariant** | `INV-ADS-002`、`REQ-ADS-ARCH-002` |

---

**`RP-006` — 低置信度**

| 字段 | 内容 |
|---|---|
| **Trigger** | `confidence < config.selector.confidence_threshold`（当前 0.5） |
| **System Action** | **视为不可信 → `no_ad`**（原因码 `low_confidence`） |
| **Evidence captured** | 原始 `confidence` 值、阈值、`ad_id`、场景特征 |
| **Escalation condition** | 降级率 > 阈值（阈值可能过紧，OQ-004）→ 用评估集重新标定；触发 `IR-004` |
| **Related invariant** | `INV-ADS-006`、`REQ-ADS-NFR-SAFETY-005` |

---

### 合规类

---

**`RP-007` — 合规过滤 REJECT**

| 字段 | 内容 |
|---|---|
| **Trigger** | compliance 管道任一步失败（`output_exists` / `banned_words` / `category` / `scene`） |
| **System Action** | **丢弃该候选 → `no_ad`**（原因码 `compliance_rejected` + 失败规则名）；**不展示** |
| **Evidence captured** | 失败规则名、命中详情（违禁词 / 品类 / 场景冲突项）、`ad_id` |
| **Escalation condition** | **`compliance_escape_count > 0` 即立即升级**（安全主张失效，重开 ADR-001 T1）；命中违禁词广告出现在素材库 → 检查素材入库流程 |
| **Related invariant** | `INV-ADS-001`、`007`、`008` |

---

**`RP-008` — 候选集为空**

| 字段 | 内容 |
|---|---|
| **Trigger** | 规则预筛后候选集大小为 0 |
| **System Action** | **跳过 LLM 调用**（省 token）→ 直接 `no_ad`（原因码 `no_candidates`） |
| **Evidence captured** | 场景特征、预筛剔除原因分布、候选集规模 = 0 |
| **Escalation condition** | 空候选率 > 阈值（素材覆盖不足）→ 扩充素材库（OQ-003） |
| **Related invariant** | `REQ-ADS-FR-003` |

---

### 可用性与成本类

---

**`RP-009` — LLM 超时或调用异常**

| 字段 | 内容 |
|---|---|
| **Trigger** | LLM 调用超过 `config.llm.timeout_sec`，或抛出异常（网络/鉴权/限流） |
| **System Action** | **timeout gate 拦截 → fallback path → `no_ad`**（原因码 `llm_timeout` / `llm_error`）；**进程不崩溃** |
| **Evidence captured** | 超时阈值、实际耗时、异常类型与消息、模型版本 |
| **Escalation condition** | p95 延迟超阈值或失败率上升 → **SLA drift alert**（`INV-ADS-013`）；持续超时 → 检查供应商（OQ-001） |
| **Related invariant** | `INV-ADS-013`、`REQ-ADS-FR-003`、`REQ-ADS-NFR-PERF-001` |

> 课程"性能陷阱"的落地：**违规必须被处理**——本策略同时强制 `timeout gate`、`fallback path`、
> `p95 监控`、`SLA drift alert` 四个元素，缺任一则 `REQ-ADS-NFR-PERF-001` 视为未实现。

---

**`RP-010` — 上下文超预算**

| 字段 | 内容 |
|---|---|
| **Trigger** | 装配后的上下文 token 达窗口 **85%**（触发 compaction）或超过上限 |
| **System Action** | 先**降级为 SUMMARIZE 路径**（压缩候选摘要）；若仍超上限 → **`no_ad`**（原因码 `budget_exceeded`）；**compaction 后重新注入 standing constraints** |
| **Evidence captured** | 各层 token 计数、是否触发 compaction、重注入是否执行、最终 prompt 的约束存在性 |
| **Escalation condition** | compaction 频繁触发（候选集持续超预算，R-003）→ 调整候选摘要策略；**重注入失败即立即升级**（安全约束可能不可见） |
| **Related invariant** | `INV-ADS-014`、`REQ-ADS-NFR-COST-001` |

> **重注入是本策略的安全要害**：课程 P165 实测 compaction 会把 Instructions 推到低注意力位置，
> 导致"规则存在但不可见"（约束满足率从 98% 降到 72%），因此重注入是 budget 步骤的**架构级强制行为**，
> 不是可选优化。

---

**`RP-011` — 审计写入失败**

| 字段 | 内容 |
|---|---|
| **Trigger** | JSONL 审计日志写入失败（磁盘满、权限、IO 错误） |
| **System Action** | **本次推荐失败（fail-closed）**，不静默继续；返回错误；写告警 |
| **Evidence captured** | 失败原因、尝试写入的记录内容（尽力落盘到备用路径） |
| **Escalation condition** | **任一次发生即升级人工**；失败率 > 阈值 → 重开 ADR-002 T-3（是否改为同步阻塞队列） |
| **Related invariant** | `INV-ADS-012`、`REQ-ADS-GOV-001` |

> 立场依据（课程行 538）：**audit logging 不可协商，token 节省不能绕过它**。

---

### 素材核验状态类

---

**`RP-017` — 素材违禁内容核验状态非 `checked`**

| 字段 | 内容 |
|---|---|
| **Trigger** | 素材的 `banned_check` 取值为 `pending`（未核验）或 `banned`（已判禁投） |
| **System Action** | **REJECT → `no_ad`**（原因码 `banned_check` + 实际状态值）。**fail-closed：仅 `'checked'` 放行** |
| **Evidence captured** | 素材 `ad_id`、`banned_check` 实际取值、本次请求场景 |
| **Escalation condition** | 生产环境出现 `banned` 素材进入候选集 → **立即升级**（核验流程失效）；`pending` 素材比例高 → 检查素材入库核验是否积压 |
| **Related invariant** | `INV-ADS-001`、`REQ-ADS-ARCH-001` |

> **为什么单列一条策略**：本字段此前被 schema 与模型声明、被全部素材填写，但**无代码读取**，
> 导致标为 `banned` 的素材仍会被展示（审计发现 `AF-004`）。该策略把"声明"变为"强制"。
> 语义要点：**`pending` 也拒绝**——未核验不等于安全，这是 fail-closed 的直接体现。

---

### 流程与治理类

---

**`RP-012` — 解释路径失败**

| 字段 | 内容 |
|---|---|
| **Trigger** | 解释生成失败，或解释质量评估不达标，或解释文本命中违禁词 |
| **System Action** | **只降级解释**（返回结构化摘要）；**`ad_id` 保持不变**；若解释含违禁词则**丢弃解释文本** |
| **Evidence captured** | 失败类型、原解释文本（仅违规场景）、决策结果是否被影响（**必须为"未影响"**） |
| **Escalation condition** | 出现任一"解释影响决策"的样本 → **立即升级**（违反 `INV-ADS-004`）；解释质量持续不达标 → 检查评估口径（OQ-009） |
| **Related invariant** | `INV-ADS-004`、`REQ-ADS-AI-001` |

---

**`RP-013` — 行为测试失败但结构测试通过（架构缺口）**

| 字段 | 内容 |
|---|---|
| **Trigger** | agent 遵守了全部架构约束、结构测试通过，但**行为/质量测试失败** |
| **System Action** | **阻断直接修改 safety-critical 代码**；要求产出**架构修订**（ADD-R：ADR + delta specification + 工件更新） |
| **Evidence captured** | 失败测试 ID、对应 REQ/INV、是否已存在 ADR、变更文件清单 |
| **Escalation condition** | 任何绕过尝试即升级人工（`INV-ADS-009`）；架构缺口累积 → 记入 `docs/debt-register.md` |
| **Related invariant** | `INV-ADS-009`、`INV-ADS-010` |

> 依据（课程行 4229/4241–4249）：**The code is CORRECT. The architecture is UNDERSPECIFIED.**
> 正确动作是改架构，不是 patch 代码。

---

**`RP-014` — 评估门未通过**

| 字段 | 内容 |
|---|---|
| **Trigger** | 固定评估集 replay 未达质量阈值（或评估集 < 20 条，或 zero-escape 校验失败） |
| **System Action** | **阻断合并（fail-closed）**；输出通过率与违规数；变更不得进入产物 |
| **Evidence captured** | replay 结果明细、失败用例、违规数、被阻断的变更 ID |
| **Escalation condition** | 安全相关阈值失败即人工复核；连续两轮失败 → 重估阈值标定（OQ-004/OQ-005） |
| **Related invariant** | `INV-ADS-016`、`REQ-ADS-NFR-QA-001` |

---

**`RP-015` — 权限或 hook 拦截（变更治理）**

| 字段 | 内容 |
|---|---|
| **Trigger** | 对 safety-critical 路径的变更缺少权限声明，或缺少配套 ADR |
| **System Action** | **拒绝该次写入**（pre-commit hook 在进入仓库前拦截） |
| **Evidence captured** | 目标路径、变更者角色、是否存在 ADR、变更摘要 |
| **Escalation condition** | 拦截记录进 `docs/debt-register.md` 并要求人工评审；反复尝试即升级 |
| **Related invariant** | `INV-ADS-010`、`REQ-ADS-GOV-002` |

---

**`RP-016` — 运行期不变量违例（兜底策略）**

| 字段 | 内容 |
|---|---|
| **Trigger** | 任一 monitor 报出不变量违例：`compliance_escape_count > 0`、`deterministic_replay_diff_count > 0`、`out_of_candidate_selection_count > 0`、`audit_entries_per_request != 1`、`post_compaction_constraint_present == false` 等 |
| **System Action** | **立即降级 `no_ad`（fail-closed）**；**冻结涉及的候选或规则**；写 CRITICAL 审计；**不继续服务该请求** |
| **Evidence captured** | 违例的不变量 ID、触发的 monitor、原始输入、LLM 原始输出、复现所需的最小输入集 |
| **Escalation condition** | **任何不变量违例即立即升级人工**（课程行 5244：**Zero invariant violations accepted**）；按 ADR-002 D3 判定归因：结构测试通过而行为失败 → **改架构（ADD-R），不要 patch 代码** |
| **Related invariant** | 全部 16 条（兜底） |

> **为什么需要这条兜底**：前 15 条策略是**按触发源**枚举的（契约、注入、解析、合规、超时……）。
> 但 monitor 可能报出设计时未预见的组合，因此架构需要一个**不变量层面的兜底响应**，
> 否则"发现违例"之后没有既定动作——那就等于 monitor 只是告警，不是强制。

---

## 2. 汇总表（快速索引）

| Policy | Trigger（简） | System Action（简） | 原因码 | Related Invariant |
|---|---|---|---|---|
| `RP-001` | 素材契约违规 | 拒绝整批加载，阻断启动 | — | `INV-ADS-015` |
| `RP-002` | 场景输入非法 | 拒绝请求，不进 LLM | — | `REQ-ADS-FR-002` |
| `RP-003` | 注入检出 | 拦截 → `no_ad` | `injection_detected` | `INV-ADS-005` |
| `RP-004` | LLM 输出非法 | 重试 1 次 → `no_ad` | `llm_output_invalid` | `INV-ADS-003` |
| `RP-005` | 集外 `ad_id` | REJECT → `no_ad` | `output_not_in_candidates` | `INV-ADS-002` |
| `RP-006` | 低置信度 | → `no_ad` | `low_confidence` | `INV-ADS-006` |
| `RP-007` | 合规 REJECT | 丢弃候选 → `no_ad` | `compliance_rejected` | `INV-ADS-001/007/008` |
| `RP-008` | 候选集为空 | 跳过 LLM → `no_ad` | `no_candidates` | `REQ-ADS-FR-003` |
| `RP-009` | LLM 超时/异常 | timeout gate → `no_ad` + drift alert | `llm_timeout` / `llm_error` | `INV-ADS-013` |
| `RP-010` | 上下文超预算 | SUMMARIZE → `no_ad` + 重注入约束 | `budget_exceeded` | `INV-ADS-014` |
| `RP-011` | 审计写入失败 | 整体失败（fail-closed） | — | `INV-ADS-012` |
| `RP-012` | 解释路径失败 | 只降级解释，`ad_id` 不变 | — | `INV-ADS-004` |
| `RP-013` | 架构缺口（行为测试失败） | 阻断改代码，要求改架构 | — | `INV-ADS-009/010` |
| `RP-014` | 评估门未通过 | 阻断合并 | — | `INV-ADS-016` |
| `RP-015` | 权限/hook 拦截 | 拒绝写入 | — | `INV-ADS-010` |
| `RP-016` | 运行期不变量违例（兜底） | 立即 `no_ad` + 冻结 + 升级人工 | — | 全部 16 条 |
| `RP-017` | 素材核验状态非 `checked` | REJECT → `no_ad`（仅 `checked` 放行） | `banned_check` | `INV-ADS-001` |

**覆盖自检**（课程要求：**每条降级路径都映射到响应**）：
`REQ-ADS-FR-003` 列举的降级场景（无候选 / LLM 失败 / 超时 / 合规全拒）分别由 `RP-008`、`RP-004`/`RP-009`、`RP-009`、`RP-007` 覆盖。
另有 10 条策略覆盖非降级但必须定义响应的失败模式（契约、注入、置信度、预算、审计、解释、架构缺口、评估门、权限、素材核验状态）。
最后 `RP-016` 以**不变量层面兜底**覆盖未预见的组合。
**共 17 条策略，无未映射的失败路径**（追踪矩阵 §1 的 22 条需求全部可映射到至少一条策略）。

---

## 3. Escalation（升级路径总则）

课程行 5176：**升级是架构安排，不是事后补丁**。本项目升级阶梯：

```
Agent / 系统自动策略（RP-001~015）
      ↓ 触发 escalation condition
人工负责人（Architecture Owner / QA Owner）
      ↓ 涉及不变量或安全声称失效
重开 ADR（adr-001 / adr-002 的 re-open trigger）
      ↓
架构修订（ADD-R：delta specification + 工件更新）
```

**立即升级（无需达阈值）的事件**：
- `compliance_escape_count > 0`（`RP-007`）
- `permission_bypass_count > 0`（`RP-015`）
- 任一"解释影响决策"的样本（`RP-012`）
- 审计写入失败任意一次（`RP-011`）
- LLM 返回集外 `ad_id` 任意一次（`RP-005`）
