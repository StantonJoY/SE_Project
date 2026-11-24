# Permission Model — 角色级文件读写权限（D2.6）

> **状态**：Accepted（派生自既有治理工件，2026-11-24 装配）
> **课程对应**：D2 第 6 件 —— *Permission model: file-level read/write rights for each AI
> coding agent's role; default is no read, no write; every path is explicitly whitelisted.*
> **唯一权威来源**：`.opencode/permissions.jsonc`（机器可读）
> 本文件是它的**人类可读视图**，不构成第二份权威。两者冲突时**以 `permissions.jsonc` 为准**，
> 并应立即在本文件登记差异（对应 `TD-027` 文档新鲜度债）。

---

## 0. 为什么需要这一层

课程要求权限模型是**默认拒绝**的：默认"不可读、不可写"，每个路径必须**显式列入白名单**。

本项目把它实现为三个互补的层：

| 层 | 载体 | 强制方式 | 能否机械拦截 |
|---|---|---|---|
| **声明层** | `.opencode/permissions.jsonc` | 人工审查 + `docs/ai-use-log.yaml` 的角色记录 | ❌ 声明本身不拦截 |
| **结构层** | `scripts/fitness_functions.py`（S1–S3、V1–V4） | CI 门禁 | ✅ |
| **执行层** | `scripts/check_safety_paths.py`（hook H-001） | CI（本地 hook 未安装，`TD-026`） | ✅ 部分 |
| **最后防线** | `.github/CODEOWNERS` + 分支保护 | GitHub | ✅ |

`permissions.jsonc` 的 `enforcement_reality.not_mechanically_enforceable` 已如实列出
"读工具的角色限制无法机械拦截"——**本文件同样不假装能拦**。

---

## 1. 六个角色（`permissions.jsonc` → `roles`）

| 角色 | 职责 | 可读 | 可写 | **不得访问** |
|---|---|---|---|---|
| **`plan`** | 产出执行计划清单（五要素），**不写代码** | `**`（全部） | `docs/plans/**` | `src/**`、`test/**` |
| **`build`** | 按已批准计划实现 | AGENTS.md、blueprint、req、architecture、code-governance、plans、`src/**`、`eval/**`、`data/**`、`.github/**` | `src/selector/**`、`src/render/**`、`src/audit/**`、`src/app/**`、`src/bidding/**`、`eval/**`、`data/bids-v2.json`、`config-v2.yaml` | **`test/**`** |
| **`verify`** | 独立验证：跑门禁、审计一致性、出合规报告 | `**` | **仅** `docs/review-memo.md` | 禁止 `modify_source_code` / `write_adr` / `modify_tests` |
| **`tester`** | 编写并维护测试 | `docs/req/requirements.yaml`、`acceptance-coverage-map.yaml`、`AGENTS.md`、`docs/plans/**` | `test/**` | **`src/**`** |
| **`human`** | 批准、决策、豁免 | `**` | `**` | 无（唯一可改 `.opencode/rules.md`） |
| **`supervisor`** | 真实用户委托的 AI proxy 技术评审 | `**` | `docs/**`、`AGENTS.md`、`Prompt.md`、`architecture-blueprint.md`、`scripts/**`、`.github/workflows/**`、`.opencode/permissions.jsonc`、`pyproject.toml`、`README.md` | `.opencode/rules.md` |

> ⚠️ 上表的「可读」「不得访问」是**声明层**的授权描述，**不是技术隔离**。
> CI 门禁只能验证**写入**与产物，**读工具无法机械拦截**（见 §5 的
> `not_mechanically_enforceable`）——这也正是本项目把"使产出可追溯"而非
> "使违规不可能"作为应对策略的原因。不要把这张表读成一张 ACL。

### 1.1 两条互斥规则（blindness invariant）

`AGENTS.md` ⑥ 与 `permissions.jsonc` 的 `P-008` 共同定义：

> **blindness invariant ①（不可协商）：BUILD 不得读测试源码。**
> 若 BUILD 能读测试，它会把测试改成匹配其破损实现——测试通过、不变量被违反、无人察觉。
> BUILD 只接收 **stripped error report**：失败测试 ID + 断言摘要，不含测试实现细节。
>
> **blindness invariant ②：TESTER 不得读 `src/` 实现。**
> 对称的隔离：TESter 只依据规格写测试，不依据实现写测试。

这条互斥是本项目"权威边界"的人格化表达：**做的人不判，判的人不做**。

### 1.2 `supervisor` 角色的特殊性（必须显式声明）

`supervisor` 是对真实用户 2026-10-30T12:10:56.447Z 授权的**代理**，`permissions.jsonc` 里写死了：

```jsonc
"proxy_review_is_human_approval": false
```

即：**AI proxy 的评审不能写成新的具名人类批准。**
它的 `forbidden_actions` 含 `forge_human_approval` / `delete_or_skip_existing_tests` / `publish_without_authorization`。

---

## 2. 路径规则（`permissions.jsonc` → `path_rules`，共 16 条）

**含义**：`agent_access` 是**默认值**；`requires` 是该路径变更时必须**额外附带**的工件。

| ID | 路径 | guard | agent 访问 | 需要 | 依据 |
|---|---|---|---|---|---|
| `P-001` | `src/compliance/**` | safety_critical | **none** | ADR + 人工批准 | `INV-ADS-001` |
| `P-002` | `src/ads/schema.py` | safety_critical | **none** | ADR + 人工批准 | `INV-ADS-007`/`008` |
| `P-003` | `data/*.json` | safety_critical | **none** | ADR + 人工批准 | `INV-ADS-007`/`008` |
| `P-004` | `docs/req/requirements.yaml` | safety_critical | read | ADR + 人工批准 | `INV-ADS-010` |
| `P-005` | `docs/architecture/invariants.md` | **human_only** | read | 人工批准 | 课程「HUMAN ONLY」 |
| `P-006` | `docs/architecture/adr-*.md` | **human_only** | read | 人工批准 | 课程「No agent may self-approve」 |
| `P-007` | `src/selector/**` | adr_on_threshold_change | write | **仅改阈值逻辑时**须 ADR + 人工批准 | `INV-ADS-006` |
| `P-008` | `test/**` | protected_from_build | build:none / tester:write / verify:read | — | `INV-ADS-011` |
| `P-009` | `eval/**` | safety_critical | read | ADR + 人工批准 | `INV-ADS-016`、`ADR-004` |
| `P-010` | `.opencode/rules.md` | **human_only** | **none** | 人工批准 | 课程 D3 human-only |
| `P-011` | `.github/workflows/**` | requires_approval | read | 人工批准 | 改 CI 即改门禁 |
| `P-012` | `pyproject.toml` | requires_approval | read | 人工批准 | 供应链面 |
| `P-013` | `scripts/check_*.py` | safety_critical | read | ADR + 人工批准 | `ADR-004` |
| `P-014` | `scripts/fitness_functions.py` | safety_critical | read | ADR + 人工批准 | — |
| `P-015` | `scripts/mutation_check.py` | safety_critical | read | ADR + 人工批准 | `INV-ADS-011` |
| `P-016` | `docs/code-governance/acceptance-coverage-map.yaml` | safety_critical | read | ADR + 人工批准 | 覆盖声明即判据 |

> **两个来源，不要混淆**：
>
> ① **上表 16 条**来自 `permissions.jsonc` 的 `path_rules`（`P-001`..`P-016`），
> 描述的是**角色级授权**（谁能写、要不要 ADR）；
> ② `scripts/check_safety_paths.py --show-paths` 另从 `ADR-002` D4、`ADR-004` D1、
> `ADR-005` 的标记表**合并解析**出 **26 条**受保护路径——这是 **CI 实际拦截的口径**。
>
> 两边**不是一一对应**：26 条里按文件逐条枚举了 `data/ads.json`、`data/banned_words.json`
> 等具体文件，而 `path_rules` 里是笼统的 `data/*.json`。前者判定"CI 拦不拦"，
> 后者判定"哪个角色可以写"。
>
> 这条分裂本身就是 `BUG-007` 的教训：**同类规则分散在多处必然漂移**。
> 本文件只做如实呈现，不声称两者已统一。

### 2.1 探针（可直接复核）

```bash
python scripts/check_safety_paths.py --show-paths
```

---

## 3. 禁止动作（`permissions.jsonc` → `deny`）

| ID | 被禁止的动作 | 强制方式 |
|---|---|---|
| `D-001` | 在未显式选择 HTTP relevance provider 时联网 | 注入边界 + 离线测试（**不声称有网络防火墙**） |
| `D-002` | 读取未声明的环境输入 | CLI 边界 + 源码审查；**环境变量访问未被沙箱限制** |
| `D-003` | 删除或跳过既有测试 | `fitness_functions.py` 的 V4（`REQUIRED_TEST_MODULES`） |
| `D-004` | 在授权计划之外修改架构 | 人工审查 |
| `D-005` | 计划获批前调用写工具 | 流程纪律 + `docs/ai-use-log.yaml` 的角色记录 |
| `D-006` | **自我批准** | `check_test_approval.py` 的 `approved_by` 校验（占位符即视为不可信） |

---

## 4. 强制机制（`permissions.jsonc` → `enforcement`）

| Hook | 事件 | 脚本 | 用途 | 状态 |
|---|---|---|---|---|
| `H-001` | pre_commit | `scripts/check_safety_paths.py` | 拦截无 ADR 的 safety-critical 变更 | ⚠️ 仅 CI（本地未装，`TD-026`） |
| `H-002` | ci | `scripts/check_test_approval.py` | 门禁 1：测试先于实现获批 | ✅ 已装 |
| `H-003` | ci | `scripts/check_ai_use_log.py` | 门禁 6：改代码/prompt 须更新 AI 日志 | ✅ 已装 |
| `H-004` | ci | `scripts/check_semantic_eval.py` | 门禁 4：prompt/model 变更须过阈值 | ✅ 已装 |

**Fitness functions**（`S1`–`S3` + `V1`–`V4`）见 `docs/code-governance/structural-constraints.md`
与 `verification-constraints.md`，此处不重复。

---

## 5. 诚实的边界：这份模型拦不住什么

`permissions.jsonc` 的 `enforcement_reality` 原文列出**无法机械强制**的部分，
本文件照录而不美化：

- **T1/T2 读工具的角色限制** —— 读取无副作用，CI 不可观测；
- **`D-002` 环境变量读取** —— 需人工审查；
- **`D-004` 架构工件改动** —— 仅人工审查可拦；
- **`D-005` 计划获批前的工具调用** —— 流程纪律，非技术拦截；
- **`P-007` 的"改动阈值逻辑"条件** —— 需人工判断何为阈值语义变更。

> **残余风险（原文）**：读工具的滥用（如 BUILD 偷看测试）在技术上无法拦截；
> 本项目的应对是**"使产出可追溯"而非"使违规不可能"**。
> 这是可接受的残余风险，但必须显式声明而非默认不存在。

### 5.1 一处已知漂移（本文件不代为修正，仅登记）

`permissions.jsonc` 的 `enforcement.branch_protection.status` 仍为
`"documented_not_yet_enabled"`，而 `docs/branch-protection.md` §9 记录了
2026-11-22 的实测：保护**已启用**、直推被拒、加 bypass 后放行。

两者不一致。**本文件不改 `permissions.jsonc`**——该文件的 `may_write` 只对
`supervisor` 角色开放，且 `P-001`..`P-016` 里没有任何一条把它列为可机械拦截的路径；
本文件只在此登记，避免本文件成为第三个错误来源。

---

## 6. 追溯

| 本文件章节 | 来源 |
|---|---|
| §1 六个角色 | `permissions.jsonc` `roles`（`version 2.0.0`, `updated_at 2026-10-31`） |
| §1.1 blindness invariant | `AGENTS.md` ⑥「角色约束」；`P-008` |
| §1.2 supervisor 特殊性 | `permissions.jsonc` `v2_authorization.proxy_review_is_human_approval = false` |
| §2 路径规则 | `permissions.jsonc` `path_rules`；`check_safety_paths.py --show-paths` |
| §3 禁止动作 | `permissions.jsonc` `deny` |
| §4 强制机制 | `permissions.jsonc` `enforcement` |
| §5 边界 | `permissions.jsonc` `enforcement_reality`（逐字转录） |
| §5.1 漂移 | `docs/branch-protection.md` §9；`docs/debt-register.md` `TD-027` |
