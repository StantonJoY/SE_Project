# .agent/rules.md —— 项目公约（Project Covenant）

> 课程对应：D3 第 6 项 —— *"the project covenant: abstraction limits, dependency constraints,
> test independence (at least one negative test per feature), the rule that changing
> safety-critical code requires an architecture decision and human approval, and
> context freshness (rules updated within one sprint of a requirements change)."*
> **状态**：草案待批 · 版本：V1 · 日期：2026-10-06
>
> **与另两份规则文件的分工**（避免三处重复 —— 那必然漂移）：
>
> | 文件 | 定位 | 变更权限 |
> |---|---|---|
> | `AGENTS.md`（根目录） | **规格入口**：读什么 / 能改什么 / 验什么 | 人类批准 |
> | `.opencode/rules.md` | **常驻行为规则**：每次会话恒定生效（R1–R10） | **HUMAN ONLY** |
> | **本文件** | **项目公约**：本项目的**自我约束承诺**，含可量化的上限 | 人类批准 |
>
> 课程为本文件列出**五项**要求，逐条对应下文 §1–§5。每项都给出**本项目当前的实际数值**，
> 使"公约"可被检验，而非只是宣告。

---

## §1 Abstraction Limits（抽象上限）

**课程要求**：约定抽象的层数与粒度上限，防止过度设计。

### 1.1 本项目的抽象上限

| 约束 | 上限 | 当前实际 | 检验方式 |
|---|---|---|---|
| **架构元素（顶层包）数** | **7**（+2 个非 `src/` 验证构件） | 7（+`eval/`、`scripts/`） | `fitness_functions.py` 的 S1 |
| **单一功能路径的调用层数** | **≤ 5 层** | 见下 | 人工审查 + 集成契约表 |
| **一个架构元素的实现文件数** | **≤ 6** | 最多 6（`src/selector/`、`src/app/`） | 目录清点 |
| **函数返回元组长度** | **≤ 3 元** | 最多 3（`run_compliance` 返回单个 Verdict 对象） | 人工审查 |
| **继承深度** | **≤ 1**（仅在确有必要时） | 0 —— 全部用 `Protocol` 结构化子类型 | 人工审查 |
| **依赖注入方式** | **构造参数注入**（不用全局单例、不用框架） | 一致 | 代码审查 |

**功能路径的 5 层上限**（本项目的唯一完整路径）：

```
cli.main (1)
  └─ app.pipeline.recommend (2)
       ├─ selector.context.ContextAssembler.assemble (3)
       │    └─ client.briefs_to_prompt_block (4)
       ├─ selector.parser.parse_llm_output (3)
       └─ compliance.pipeline.run_compliance (3)
            └─ check_* (4)                    ← 五步管道各检查函数
```

**为什么设上限**：课程把"架构元素恰好映射一个模块"作为结构约束（S1）。
抽象层数失控会让 S1 的检查失去意义 —— 元素还在，但每个元素内部又长出一个小系统。

**超出上限时的动作**：**停止并修订架构**（`ADR-002` D3 的 ADD-R），
不得以"再加一层就好"的方式就地扩写。

### 1.2 明确不引入的抽象（反面清单）

| 不引入 | 理由 |
|---|---|
| ORM / 数据库抽象层 | V1 用 JSON + JSONL（`memory-design.md` §3）；引入 ORM 是为不存在的需求付复杂度 |
| 消息队列 / 异步框架 | 本项目是**请求-响应**的纯函数管道；异步会破坏确定性（`REQ-ADS-ARCH-004`） |
| 插件系统 / 动态注册 | 7 个元素静态映射，动态发现只会让 S1 不可检查 |
| DI 容器 | 构造参数注入已足够；容器会把依赖关系变成运行期才知道的事 |
| 通用"策略引擎" | `compliance` 的五步是**固定顺序**，不是可配置的策略链 —— 顺序本身就是安全属性 |
| 缓存层 | V1 无状态（`memory-design.md`）；缓存会引入"同一输入不同输出"的风险 |

---

## §2 Dependency Constraints（依赖约束）

**课程要求**：约定依赖方向与可接受的依赖。

### 2.1 允许的依赖方向（单向，不可逆）

```
data (JSON)  ──→  ads  ──┐
                         ├──→  compliance  ──┐
scene  ──────────────────┘                  ├──→  app
                                            │
selector  ──────────────────────────────────┤
render  ────────────────────────────────────┤
audit  ─────────────────────────────────────┘
```

| 依赖 | 允许 | 依据 |
|---|---|---|
| `app` → 任何元素 | ✅ | `app` 是编排层，唯一允许同时 import `selector` 与 `compliance` 的地方 |
| `selector` → `ads` | ✅ | 只读类型与违禁词检查（解释复查用） |
| `selector` → `compliance` | ❌ **禁止（双向）** | 权威边界会倒置 —— 由 `fitness_functions.py` 的 S2 **机械强制** |
| `compliance` → `selector` | ❌ **禁止** | 裁决层不得知道建议层如何实现 |
| `compliance` → `audit` | ❌ | 合规是纯函数（可复现），写审计会引入副作用 |
| `render` / `audit` → 其他 | ✅ 仅只读 | 二者是终端：`render` 表达结果、`audit` 记录证据 |
| `eval` → `app` | ✅ | `ADR-003` D5：**必须走完整管道**，不得直接调 compliance 或 selector 内部函数 |
| `scripts` → 任何 | ✅ 只读 | 检查器只读，不得改被测对象 |
| 任何元素 → `eval` | ❌ **禁止** | `ADR-003` D7：评估集**运行时不可见**（blindness 对偶） |

### 2.2 依赖面约束

| 约束 | 当前声明 | 检验方式 |
|---|---|---|
| **运行时依赖数量** | **3 个**（`jsonschema`、`PyYAML`、`tomli`（py<3.11）） | `pyproject.toml` |
| **开发依赖** | `pytest`、`ruff`、`mypy`、`types-jsonschema` | `pyproject.toml` |
| **禁止的网络库** | `requests`、`httpx`、`openai`、`urllib`、`socket` | `check_dependencies.py`（`[tool.depcheck]`） |
| **隐藏依赖** | **零容忍** —— 代码实际 import 而未声明即 FAIL | `check_dependencies.py` 检查 ② |
| **臃肿声明** | **零容忍** —— 声明了但从未使用即 FAIL | `check_dependencies.py` 检查 ④ |
| **跨包相对导入** | **禁止** —— 一律绝对导入 | `structural-constraints.md` §1 |

**新增依赖的门槛**：须人工批准（`.opencode/permissions.jsonc` 的 P-012）。
判据：**它替代的是多少行自写代码，以及它引入多少供应链面**。
`jsonschema` 留着（自写 schema 校验器更危险），而 `tiktoken` 被**刻意拒绝**
（`selector/context.py` 用 `ceil(len/3)` 的保守估算，见该模块的说明）。

### 2.3 依赖的"零第三方"边界

`src/` 的全部**安全逻辑**（`compliance/`、`ads/schema.py`）**只依赖标准库与 `jsonschema`**。
理由：安全判据不应随第三方库的版本行为而改变。

---

## §3 Test Independence（测试独立性）

**课程要求**：每个功能**至少一个反例测试**（negative test）。

### 3.1 本项目的落实

| 要求 | 落实 | 检验方式 |
|---|---|---|
| **每个功能 ≥1 反例测试** | 每条不变量 ≥1 个**会失败**的测试 | `fitness_functions.py` 的 V2 |
| **反例必须真的会失败** | **变异验证**：13 条不变量各注入一条违规，确认测试失败 | `scripts/mutation_check.py`（**13/13 已检出**） |
| **测试引用其验证的 ID** | 每个测试 docstring 含 REQ/INV ID | `fitness_functions.py` 的 V3 |
| **测试独立于实现细节** | 测试直调**公共 API**；不测私有函数 | 人工审查 |
| **测试不得相互依赖** | 无共享可变状态；fixture 为 `module`/`function` 作用域 | 人工审查 |
| **无回归** | 既有测试模块不得消失 | `fitness_functions.py` 的 V4（15 个模块） |

**当前规模**：**285 个离线测试**；覆盖 **21/22** 需求、**13/16** 不变量
（计数由脚本核对，见 `acceptance-coverage-map.yaml`）。

### 3.2 "反例测试"的定义（本项目的严格化）

课程只要求"至少一个反例"。本项目进一步要求**反例具备证伪能力**：

> 一个反例测试若在**实现被破坏时仍然通过**，它就不是反例 —— 它是一段**装饰**。

这正是变异验证存在的原因。它的第一次运行就抓到了 **4 条不具备证伪能力的反例**
（其中 2 条是"补丁打错绑定"导致的**假通过**，见 `scripts/mutation_check.py` 的
`why_bound_here` 字段）。**若没有变异验证，这 4 条会一直伪装成已覆盖。**

### 3.3 测试布局约束

| 约束 | 说明 |
|---|---|
| 位置 | 确定性测试在 `test/offline/`；依赖 API 的在 `test/live/`（P8 后才有内容） |
| **禁止 `pytest tmp_path`** | 受限沙箱下子进程无法建临时目录；用 I/O 边界打桩替代（`BUG-001` 的教训） |
| 反例标记 | 反例测试的 docstring 须含 `反例` / `negative test` / `must fail` / `会失败` 之一（V2 的判定依据） |
| 归属 | 测试由 **TESTER** 角色编写（`test/` 对 BUILD 不可访问） |

---

## §4 Safety-Critical Changes Require ADR + Human Approval

**课程要求**：改动 safety-critical 代码须有架构决策与人工批准。

### 4.1 本项目的落实

- **路径清单的唯一来源**：`docs/architecture/adr-002-fail-closed-and-governance.md` §2 D4
  **加上** `docs/architecture/adr-004-verification-plane-protection.md` D1（验证平面）。
  `scripts/check_safety_paths.py --show-paths` 可打印当前 **19 条**及**清单来源的 ADR**。
- **强制方式**：提交信息须**引用 ADR ID**，否则 CI **FAIL**（已实测）。
- **不在此重复清单** —— 两处列举必然漂移（`BUG-007` 的教训：同类规则分散在多处必然漂移）。
- **新增受保护路径的流程**（`ADR-004` D3）：新建一份 ADR，放入
  `<!-- safety-critical-paths -->` 标记，紧随其后放路径表 ——
  **不必改写已冻结的 ADR，也不必改检查器代码**。

### 4.2 为什么"人工批准"不可省

课程 §11.3：**No agent may self-approve**。

> agent 可以**提出**架构决策（写 ADR 草案），但**不能批准**它。
> 若 agent 能自批，`ADR-001`/`ADR-002`/`ADR-003` 的"Accepted"状态就毫无信息量 ——
> 它只表示"agent 写完了"，不表示"人类判断过"。

**本项目的执行证据**：`docs/architecture/adr-001/002/003` 的状态均为 `Accepted`，
批准者字段为**具名人类**（Shane），并有批准指令的原文记录。
`docs/test-approvals.yaml` 中 `approved_by` 为占位符的记录**不被采信**（`check_test_approval.py`）。

### 4.3 已声明的例外（诚实清单）

| 例外 | 内容 | 登记 |
|---|---|---|
| P5/P6 的治理顺序倒置 | 人类指示"先跑通"，测试与实现同批产出、计划未先行 | `TD-023`（**未掩盖**，且 P7 已纠正） |
| 历史提交无门禁 | 2026-09-30 的 4 次提交未经任何门禁 | `TD-018` |
| 早期测试无事前批准 | 批准机制建立前写成的测试 | `TD-021`（引导悖论） |

> **本公约的可信度取决于这些例外是否被如实记录。**
> 一个从不承认例外的公约，实际含义是"没人检查过"。

---

## §5 Context Freshness（上下文新鲜度）

**课程要求**：规则在**需求变更后一个 sprint 内**更新。

### 5.1 本项目的落实

`docs/req/requirements.yaml` 变更后，须在**一个 sprint 内**检查并更新下列文件：

| # | 文件 | 为什么 |
|---|---|---|
| 1 | `AGENTS.md` ④⑤ | 模块组织与集成契约直接由元素分解导出 |
| 2 | `docs/code-governance/structural-constraints.md` | S1–S3 与 A1–A8 权威边界 |
| 3 | `.opencode/rules.md` | 常驻行为规则 |
| 4 | `.opencode/permissions.jsonc` | 路径规则与角色授权 |
| 5 | `.agent/rules.md`（本文件） | 公约的量化上限 |
| 6 | `docs/code-governance/acceptance-coverage-map.yaml` | 新增需求须登记测试去向 |
| 7 | `docs/architecture/trace-matrix.md` | 新增需求须有强制组件与 monitor |
| 8 | `README.md` 的交付物状态表 | 对外第一印象，最易过时 |

### 5.2 新鲜度**不会自动维持**（本项目的实证）

**已发生的漂移实例**（全部已修正，但它们是证据）：

| 漂移 | 发现方式 |
|---|---|
| `README.md` 写"7 个元素中 4 个为空目录"（P4/P5/P6 之后早已不成立） | 人工核对 |
| `AGENTS.md` ① 写"构建剩余模块"（已无剩余） | 人工核对 |
| `architecture-blueprint.md` §4 标 `eval/` 为"⏳ P7 待建"（P7 已完成） | 人工核对 |
| `AGENTS.md` ④ 缺 `config.py` / `__main__.py` | 人工核对 → `TD-024` |

**结论**：**四次漂移全部靠人工发现，没有一次靠机制发现。**
这是因为"文档与实现一致"目前**不可机械检验**。

### 5.3 缓解与残留

| 缓解 | 状态 |
|---|---|
| `TD-024` 的处置确立了"文档补登记"的流程 | ✅ 已执行 |
| `fitness_functions.py` 的 TRACE 检查核对追踪矩阵与需求注册表 | ✅ 已实现（但只覆盖这两者之间） |
| 每次会话结束前的自查（本公约 §5.1 的 8 项清单） | ⚠️ **流程纪律，非机械** |
| "文档-实现一致性"的自动检查 | ❌ **未实现**（登记为 `TD-027`） |

> 本节刻意留一条**未实现的检查**在册，而不是宣称"新鲜度已保证"。
> 课程把 context freshness 列为公约要求，本项目**部分满足**：流程已定义、机制待补。

---

## 公约的自我检验（可复跑的数值）

| 公约项 | 声明 | 当前实际 | 命令 |
|---|---|---|---|
| §1 元素数 ≤ 7 | 7 | 7 | `python scripts/fitness_functions.py`（S1） |
| §1 单元素文件数 ≤ 6 | 6 | max 6 | 目录清点 |
| §2 运行时依赖 = 3 | 3 | 3 | `python scripts/check_dependencies.py` |
| §2 selector ↮ compliance | 双向禁止 | ✅ 无违规 | `python scripts/fitness_functions.py`（S2） |
| §3 每不变量 ≥1 反例 | 16/16 声明 | **13/13 有变异且全部被检出** | `python scripts/mutation_check.py` |
| §3 测试总数 | — | **285** | `pytest test/offline -q` |
| §4 safety-critical 须 ADR | 9 条路径 | ✅ **19 条**已实测拦截 | `python scripts/check_safety_paths.py --show-paths` |
| §5 新鲜度 8 项清单 | 已定义 | ⚠️ 人工执行（`TD-027`） | — |

---

## 附：本文件的派生追溯

| 章节 | 课程要求 | 来源工件 |
|---|---|---|
| §1 抽象上限 | abstraction limits | `architecture-blueprint.md` §4；`structural-constraints.md` §1 |
| §2 依赖约束 | dependency constraints | `AGENTS.md` ④⑤；`check_dependencies.py`；S2 检查 |
| §3 测试独立性 | test independence（每功能 ≥1 反例） | `verification-constraints.md`；`mutation_check.py`；V1–V4 |
| §4 safety-critical + 人工批准 | 须 ADR + human approval | `ADR-002` §2 D4；`INV-ADS-010`；课程 §11.3 |
| §5 上下文新鲜度 | updated within one sprint | 课程 D3；`TD-024`、`TD-027` |
| 自我检验表 | 使公约可检验 | `fitness_functions.py`、`check_dependencies.py`、`mutation_check.py` |
