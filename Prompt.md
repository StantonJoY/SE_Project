# Prompt.md — 当前 V3 启动指令（D9）

> **V3 状态（2026-11-25）**：本文件是**静态启动指令**（课程 D9）。
> 现行的版本化运行时提示词在 [`prompts/prompt_v1.1.yaml`](prompts/prompt_v1.1.yaml)，
> 对应代码常量 `src/selector/context.py`（`ctx-v1.1`）与 `src/selector/relevance.py`（`relevance-v2.2`）。
> 下面 V2 段保留为历史快照。

> **V2 当前指令（2026-10-31）**：原课程 PDF、真实用户指令及 `docs/plans/V2-execution.md` 为本轮依据。以下 V2 段优先于后面的 V1 历史快照；历史文字保留供审计，不把其 docs2、整包冻结或尚未启动描述当作当前门槛。`.opencode/rules.md` 保持 human-only。

## V2 当前构建与授权

真实用户在 2026-10-30T12:10:56.447Z 授权本地完成 V2，并委托监督代理与实际 agent 交互。计划及技术测试设计由 AI proxy 审查，**不能写成新的具名人类批准**。正式验收状态为 `docs/v2-approval-status.yaml` 的 pending_human_acceptance；既有四条测试批准原样保留，门禁 1 在证据不足时应阻断。

有效需求仍在 `docs/req/requirements.yaml`，22 条 V1 + 原有 19 条 V2 ID。版本策略显式声明 V1/V2；不删除版本校验。读 ADR-005、V2 ASR/INV/trace/memory/runtime 增量及原 V1 安全边界后按计划实现。

| 当前模块 | 职责与公开契约 |
|---|---|
| `src/bidding/models.py` | `Bid`、`BidError`、`validate_bids`，报价 sidecar 校验 |
| `src/bidding/engine.py` | `AuctionChoice`、`choose_winner`，relevance*bid、ad_id 平局、pay_as_bid |
| `src/bidding/ledger.py` | `Ledger.seed/budgets/lookup/finalize/close`，预算+结果+审计同事务；`audit_records` 仅离线验证 |
| `src/selector/relevance.py` | `RelevanceClient.score`、`FixedRelevanceClient`、`HTTPRelevanceClient`、`parse_relevance_output` |
| `src/app/pipeline_v2.py` | `recommend_v2`：sanitize → 模型建议 → 确定性竞价 → FINAL AUTHORITY 合规 → 原子结算 |
| `src/app/cli_v2.py` | 严格配置加载、持久 SQLite、显式 HTTP/env 名称边界 |
| `src/render/schema_v2.py` | `validate_v2_result`，ad / no_ad / status_unknown |
| `eval/v2_runner.py`、`eval/v2_cases.json` | 独立 V2 固定评估，和 V1 一起由语义门禁调用 |

允许范围：新增 V2 模块/数据/config/test/eval，原需求和架构目录增量维护，必要治理脚本/CI 修正；不改原 V1 安全规则或删除/跳过既有测试，不修改 `.opencode/rules.md`，不提交密钥、不推送。BUILD 不修改 TEST 的断言；独立 TEST 依据规格先写测试。监督/VERIFY 可读取实现与测试以诊断契约差异，需记录角色与干预，不将历史互盲约定当作禁止必要评审的课程硬条。

运行时只允许显式配置的 HTTP relevance 请求；V2_LLM_API_KEY 是环境变量名称，值不入库、不打印、不进入审计。默认 fixed，离线测试/CI 禁止 live API。预算是跨请求持久状态，不能每次 seed 重置。

验证：需求 schema → fitness 实际 V2 enforcement/证据函数检查 → V1+V2 全量回归（含 bidding >=90% 语句覆盖）→ 两套固定 replay。语义触发覆盖 Python prompt、竞价、pipeline、bids、config。无可信正式批准、未跟踪新文件、远程保护未验证或真实模型未测时必须如实报告；不得为变绿自我批准或自动 git add。

## V1 历史快照（原文保留）

# Prompt.md — 静态启动指令（D9）

> **本文件是启动指令，不是让 agent 无人值守跑到完成的脚本。**
> 课程 D9 原文：
> *"The prompt is the launch instruction — it does not run the agent unattended to completion."*
>
> **读法**：先读 `AGENTS.md`（D3 治理入口），再读本文件。此后**本文件是唯一要读的那一个 prompt**。
> 状态：定稿待批 · 版本：V1 · 日期：2026-10-06

---

## 0. 你现在要做的事

你要在 `SE_Project` 中继续构建 **V1 场景化广告推荐引擎**。

**但你现在不许写任何代码。**

你的第一个交付物是**执行计划清单**，然后**停下来等人类批准**。

---

## 1. 先读（按顺序，不可跳读）

```
AGENTS.md                                    ← 治理入口：读什么 / 能改什么 / 验什么
docs/req/requirements.yaml                   ← 需求单一来源
docs/architecture/asr-register.md            ← 哪些需求强制结构决策（A1）
docs/architecture/invariants.md              ← 16 条不变量与 fail-closed fallback（A2）
docs/architecture/adr/001-guarded-hybrid.md  ← 权威边界：谁决策、谁检查、谁必须不行动
docs/architecture/adr/002-fail-closed-and-governance.md
architecture-blueprint.md                    ← 11 节可执行约束
docs/architecture/trace-matrix.md            ← 每条需求的强制组件 + 测试 + 运行时 monitor
docs/architecture/runtime-policy-catalog.md  ← 17 条失败策略（RP-001~017）
docs/code-governance/structural-constraints.md
docs/code-governance/verification-constraints.md
docs/execution-plan-template.md              ← 你要填的模板
```

**`AGENTS.md` §② 给出完整阅读顺序（13 项）。读完再往下。**

---

## 2. 硬性禁令（违反即架构违规）

在计划获批之前：

- ❌ **禁止输出任何源代码**
- ❌ **禁止修改任何文件**（包括"顺手改一下文档"）
- ❌ **禁止调用执行类工具**（写文件、跑构建、提交）

在计划获批之后，实现期间：

- ❌ 不得修改 `src/ads/`、`src/scene/`、`src/compliance/`（已冻结）
- ❌ 不得修改 `data/` 下任何 JSON
- ❌ 不得删除或跳过任何既有测试
- ❌ 不得新建未在 `AGENTS.md` ④ 登记的顶层包
- ❌ 不得对**安全关键路径**动手而无 ADR（清单见 `scripts/check_safety_paths.py --show-paths`）
- ❌ **BUILD 角色不得读取 `test/` 下任何测试文件**（课程 blindness invariant ①）
  —— 你只能接收 **stripped error report**（失败测试 ID + 断言摘要）
- ❌ 不得为通过门禁而**伪造空测试**或**凭空编造需求 ID**

---

## 3. 你的第一个交付物：执行计划清单

把 `docs/execution-plan-template.md` 复制为 `docs/plans/<TASK-ID>-<slug>.md`，填写**五个部分**：

| # | 部分 | 你必须给出 |
|---|---|---|
| **①** | **Traceability** | 本次构建覆盖的 `REQ` / `INV` / `ASR` ID（**必须真实存在**）、`fit_criteria`、`test_design` |
| **②** | **Interface Contract** | 目标文件的类／函数、`public_methods` 的签名、返回类型、异常 |
| **③** | **Scope Boundaries** | `target_files`（**只允许**这些）、`allowed_imports`、`prohibited_imports`、数据访问、**未触及的冻结路径** |
| **④** | **Testing Strategy** | 每个测试用例 ↔ 它验证的 `fit_criterion` / `invariant`，含**类型**与 **mock** |
| **⑤** | **Implementation Steps** | 有顺序依赖的具体动作 + 每步自验方式 + 回滚方式 |

**五要素防止的失效**（课程 §9.4）：范围蔓延 / 错误签名 / 违禁导入与沙箱逃逸 /
测试验证错误的标准 / 步骤缺失与隐藏假设。

**自检后再提交**：

```bash
python scripts/validate_requirements.py    # 你引用的 REQ/INV/ASR 是否真实存在
python scripts/fitness_functions.py        # 结构约束是否会被你的计划违反
```

---

## 4. 停下来

产出计划后：

1. **不要继续写代码。**
2. 把计划交给人类评审，并请求批准。
3. 在 `docs/execution-plan-template.md` 末尾的「人工批准记录」中填入具名批准者——**你自己不能批准**
   （课程 §11.3：**No agent may self-approve**）。
4. 若结论是 `CHANGES REQUIRED` 或 `REJECTED`：**修订计划**，不得跳到代码。

---

## 5. 获批之后：构建与自验，每阶段都有人工闸门

按计划的 ⑤ 逐步实现，**每步之后**运行本地门禁（等价于 CI）：

```bash
ruff check src test scripts                  # 门禁 2 · lint
mypy                                         # 门禁 2 · 类型
python scripts/check_dependencies.py         # 门禁 2 · 依赖
python scripts/check_safety_paths.py --base origin/main   # 门禁 2 · 安全路径 + ADR
python scripts/fitness_functions.py          # Tier 1 · 架构 fitness function
python scripts/validate_requirements.py      # 门禁 3 · Schema
pytest test/offline -q                       # 门禁 5 · 回归
python scripts/audit_implementation.py       # 实现 ↔ 需求一致性
python scripts/check_ai_use_log.py --base origin/main     # 门禁 6 · AI-use 日志
```

**任何一步失败即停，先修再往下。** 三层验证不可跳层（`verification-constraints.md` §6）。

**实现完成后**，你还必须更新（否则门禁会阻断）：

- `docs/ai-use-log.yaml` —— 追加一条 entry（门禁 6 强制）
- `docs/architecture/trace-matrix.md` —— 相应需求的 Status 由 `design` 改为 `tested`
- `docs/code-governance/acceptance-coverage-map.yaml` —— 把 `test_backed` 改为 `true` 并填证据
- `docs/debt-register.md` —— 关闭或更新被本次实现触及的技术债

**每阶段结束都要有人工评审**，不是一次性批准后放行到底。

---

## 6. 遇到这些情况，停下来问人

| 触发 | 你必须做什么 |
|---|---|
| 计划需要偏离（文件、导入、接口变了） | **停止**，重新产出计划并再获批准。计划是契约 |
| 需要修改安全关键路径 | **停止**，先产出 ADR 并取得人工批准 |
| 发现某条不变量在设计上无法被强制 | **停止**，走 ADD-R 修订架构（`INV-ADS-009`） |
| **行为测试失败而结构测试通过** | **停止**——这是**架构缺口**，正确动作是**改架构（ADD-R），不是改代码**（`ADR-002` D3）。课程原话：*The code is CORRECT. The architecture is UNDERSPECIFIED.* |
| 需要放宽任何合规 gate 以提升出广告率 | **禁止**（`concern-clusters.md` §3 裁决第 6 条） |
| 想引入"重试后展示次优候选"（使 `INV-ADS-003` 变为 fail-open） | **停止**，重开 `ADR-001` 触发器 T2 |
| 发现需求未覆盖某个 concern | **停止**，先补需求与 ASR，再谈实现 |

---

## 7. 当前可开工范围（截至 2026-10-06）

**⚠️ 当前状态：不得开工任何 `src/` 实现。**

原因：两个架构决策仍为 `Proposed`，且两个影响设计的产品问题未决。

| 前置条件 | 状态 | 影响 |
|---|---|---|
| `ADR-001`（Guarded Hybrid） | ⏳ `Proposed` | 全部实现 |
| `ADR-002`（fail-closed 与治理） | ⏳ `Proposed` | 失败语义、权限 |
| `OQ-009`（"解释"的领域口径） | ⏳ 未决 | **`src/selector/` 的解释路径无法验收** |
| `OQ-004`（置信度阈值 0.5 是否合适） | ⏳ 未决 | 阈值 gate 形同虚设 |

**当前唯一可做的构建目标是补齐 D8 的缺口**（见 `docs/debt-register.md` `TD-020`）：

```
P4  src/selector/   ← AI 建议层（课程硬性要求的「真实 AI 组件」）
P5  src/app/        ← 编排 + 降级路径
P6  src/render/     ← 输出契约
P6  src/audit/      ← 证据子系统（同时落地 22 条运行时 monitor）
```

**这四个模块的设计已完备**（ASR／不变量／模块与集成契约／失败策略均已就位），
**缺的只是代码**。但上述四个前置条件未满足前动工即返工。

---

## 8. 记住核心命题

> **AI 是顾问，代码是执行官。**
>
> LLM 只能从候选集内选择，不得自创广告；compliance 五步管道
> （`output_exists → banned_words → banned_check → category → scene`）是 FINAL AUTHORITY，
> **不可被任何路径绕过**。不确定时**不出广告**（`no_ad` 是 fail-closed 终态）。

你的工作是在**不削弱这条边界**的前提下补齐实现。**若你的改动让某条不变量变得无法强制，
那不是实现问题，是架构问题——停下来改架构。**
