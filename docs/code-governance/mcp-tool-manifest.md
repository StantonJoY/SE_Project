# MCP Tool Manifest —— 编码 agent 可调用的工具与角色授权（D3）

> 课程对应：D3 第 3 项 —— *"`docs/code-governance/mcp-tool-manifest.md` — the tools the coding
> agent may call, and which roles may call them."*
> **状态**：草案待批 · 版本：V1 · 日期：2026-10-06
>
> **本文件的作用**：把 `AGENTS.md` ⑥ 的角色约束、`structural-constraints.md` §4 的 A1–A8
> 权威边界、以及 `ADR-002` §2 D4 的 safety-critical 清单，**收敛为一张"谁能调什么"的表**。
> 它是**授权声明**，不是实现 —— 机器可读的强制形式在 `.opencode/permissions.jsonc`。
>
> **追溯**：每条授权都引用一个 ADR 章节、一个不变量 ID 或一条结构约束，**无凭空发明**（课程行 3773/3787）。

---

## 1. 三个角色的定义

源自 `AGENTS.md` ⑥ 与课程行 3683–3684、3660：

| 角色 | 职责 | 可读 | 可写 | **绝不可访问** |
|---|---|---|---|---|
| **PLAN** | 产出执行计划清单（`docs/execution-plan-template.md` 五要素），**不写代码** | 全部架构工件 + 计划模板 | `docs/plans/` | `src/`、`test/`（计划阶段不应看实现） |
| **BUILD** | 按已批准的计划实现代码 | 架构工件、`AGENTS.md`、**stripped error report** | `src/selector/`、`src/render/`、`src/audit/`、`src/app/`、`eval/`（增量） | **`test/` 下任何测试文件**（blindness invariant ①） |
| **VERIFY** | 独立验证：跑门禁、审计一致性、出合规报告 | 全部 | 仅合规报告 | 修改代码、写 ADR、改测试 |
| **TESTER** | 编写并维护测试 | `requirements.yaml`、fit criteria、**接口契约**（`AGENTS.md` ④⑤） | `test/` | **`src/` 下任何实现文件**（blindness invariant ②） |
| **HUMAN** | 批准、决策、豁免 | 全部 | 除 `.opencode/rules.md` 外全部（该文件 human-only） | — |

> **为什么 BUILD 不能读测试**（课程 blindness invariant ①，不可协商）：
> 若 Build 能读测试，它会把**测试改成匹配其破损实现** —— 测试通过、不变量被违反、无人察觉。
> Build 只接收 **stripped error report**：失败测试 ID + 断言摘要，**不含测试实现细节**。
>
> **本项目的落地证据**：`docs/plans/P7-eval.md` §4 的测试策略表是 BUILD 在设计测试时
> 可读的部分（接口与规格），而 `test/offline/*.py` 的具体断言对 BUILD 不可见。

---

## 2. 工具清单与角色授权

课程未规定工具名的具体形式，故本表按**工具类别**声明（实现无关），
并在 `enforcement` 列给出本项目的实际强制手段。

### 2.1 只读类（无副作用）

| # | 工具 | PLAN | BUILD | VERIFY | TESTER | enforcement |
|---|---|---|---|---|---|---|
| T1 | `read_file` — 读取文本文件 | ✅ | ✅（受 §3 的路径限制） | ✅ | ✅（受 §3 限制） | 角色约束由 `.opencode/permissions.jsonc` 声明；CI 不强制（不可观测） |
| T2 | `glob` / `grep` — 按路径/内容检索 | ✅ | ✅ | ✅ | ✅ | 同上 |
| T3 | `run_checker` — 运行治理检查器<br>（`validate_requirements` / `fitness_functions` / `check_*` / `audit_implementation`） | ✅ | ✅ | ✅ | ✅ | **CI 强制**：门禁 2/3/5 直接调用 |

### 2.2 写入类（有副作用 —— 高风险，逐项授权）

| # | 工具 | PLAN | BUILD | VERIFY | TESTER | 约束与 enforcement |
|---|---|---|---|---|---|---|
| T4 | `write_file` → `docs/plans/` | ✅ | ❌ | ❌ | ❌ | 计划是 PLAN 的专属产出 |
| T5 | `write_file` → `src/**`（NEW 层） | ❌ | ✅ | ❌ | ❌ | 仅 `src/selector/`、`src/render/`、`src/audit/`、`src/app/`；**S1 检查**强制元素↔模块映射 |
| T6 | `write_file` → `test/**` | ❌ | ❌ | ❌ | ✅ | **blindness invariant ①/②**：BUILD 不得写测试 |
| T7 | `write_file` → `docs/architecture/**` | ❌ | ❌ | ❌ | ❌ | 架构工件属 **HUMAN ONLY**（课程行 5183）；`invariants.md` 在 D4 受保护清单内 |
| T8 | `write_file` → `data/*.json` | ❌ | ❌ | ❌ | ❌ | **safety-critical**：须 ADR + 人工批准（`ADR-002` §2 D4） |
| T9 | `write_file` → `src/compliance/**` | ❌ | ❌ | ❌ | ❌ | **FINAL AUTHORITY**：须 ADR + 人工批准（`INV-ADS-001`） |
| T10 | `write_file` → `.opencode/rules.md` | ❌ | ❌ | ❌ | ❌ | **HUMAN ONLY**（课程 D3 明示）；机器不可改 |
| T11 | `write_file` → `eval/**` | ❌ | ⚠️ **须 ADR** | ❌ | ❌ | **`ADR-004` D1 已将其纳入受保护路径** —— 评估集是门禁 4 的判据来源（原为 `TD-025` 的漏洞，已关闭） |

### 2.3 执行类（会改变环境 —— 最高风险）

| # | 工具 | PLAN | BUILD | VERIFY | TESTER | 约束与 enforcement |
|---|---|---|---|---|---|---|
| T12 | `run_tests`（pytest） | ❌ | ✅（**仅运行**，不得修改测试） | ✅ | ✅ | 运行测试 ≠ 读测试源码：BUILD 只接收 stripped error report |
| T13 | `run_lint` / `typecheck`（ruff / mypy） | ✅ | ✅ | ✅ | ✅ | **CI 门禁 2** |
| T14 | `git_commit` | ❌ | ✅（**须计划已批准**） | ❌ | ❌ | 提交信息须引用 ADR ID（若触及 safety-critical） |
| T15 | `git_push` / `open_pr` | ❌ | ✅ | ❌ | ❌ | **分支保护**：6 道门禁须全绿（`docs/branch-protection.md`） |
| T16 | `run_mutation_check` | ❌ | ✅ | ✅ | ❌ | 变异验证（`INV-ADS-011`）；**只注入内存变异，绝不改源文件**。注意 `scripts/mutation_check.py` 本身受 `ADR-004` 保护 |
| T17 | `run_eval_replay`（`eval/eval_runner.py`） | ✅ | ✅ | ✅ | ✅ | **CI 门禁 4**；`ADR-003` D5 要求走**完整管道** |
| T18 | `install_dependency`（改 `pyproject.toml`） | ❌ | ⚠️ **须人工批准** | ❌ | ❌ | 依赖面变更影响安全与供应链；`check_dependencies.py` 强制声明一致 |
| T19 | `modify_ci_config`（`.github/workflows/`） | ❌ | ⚠️ **须人工批准** | ❌ | ❌ | 改 CI = 改门禁本身；属 `ADR-002` D4 精神范围内 |
| T20 | `write_file` → `scripts/check_*.py`、`scripts/fitness_functions.py`、`scripts/mutation_check.py`、`docs/code-governance/acceptance-coverage-map.yaml` | ❌ | ⚠️ **须 ADR** | ❌ | ❌ | **`ADR-004` D1**：验证平面的其余成员 —— 改它们即让门禁或覆盖声明失真 |
| T21 | `install_hooks`（`scripts/install_hooks.py`） | ❌ | ✅ | ✅ | ❌ | 只写 `.git/hooks/`（不在版本控制内）；用于关闭 `TD-026` 的绕过路径 |

### 2.4 禁止类（任何角色都不可调用）

| # | 工具 | 理由 |
|---|---|---|
| X1 | 任何**网络访问**（真实 LLM API、外部 HTTP） | V1 离线；真实 LLM 接入属 P8 且须先定 `OQ-001`。BUILD 期间联网会绕过 `MockLLM` 的确定性前提 |
| X2 | 任何**环境变量读取**（`os.environ`） | 配置只走 `config.yaml`（配置治理规则 1、4）；读环境变量会引入不可审计的隐式输入 |
| X3 | **修改或删除既有测试** | `INV-ADS-011`；`fitness_functions.py` 的 V4 检查会 FAIL |
| X4 | 修改 `docs/architecture/invariants.md` | 课程行 5183：**HUMAN ONLY** |
| X5 | 调用类工具**在计划获批之前** | 课程行 3830 MANDATE |

---

## 3. 路径级授权（与 `ADR-002` §2 D4 + `ADR-004` D1 对齐）

**safety-critical 清单的唯一来源是 ADR**（`scripts/check_safety_paths.py` 从**带
`<!-- safety-critical-paths -->` 标记的表格**解析并合并多份 ADR，不在此硬编码 ——
避免两处漂移）。当前共 **19 条**，来自 `ADR-002` D4（9 条）与 `ADR-004` D1（10 条）：

| 路径 | PLAN | BUILD | TESTER | 人工必须？ |
|---|---|---|---|---|
| `src/compliance/` | 读 | **无访问** | **无访问** | **是 — 须 ADR** |
| `src/ads/schema.py` | 读 | **无访问** | **无访问** | **是 — 须 ADR** |
| `data/*.json` | 读 | **无访问** | **无访问** | **是 — 须 ADR** |
| `docs/req/requirements.yaml` | 读/写 | 读 | 读 | **是 — 须 ADR** |
| `docs/architecture/invariants.md` | 读 | 读 | 读 | **是（HUMAN ONLY）** |
| `src/selector/` | 读 | 写（guarded） | 读 | 改动**阈值逻辑**时须 ADR |
| `src/render/`、`src/audit/`、`src/app/` | 读 | 写 | 读 | 否（新增层） |
| **`eval/eval_cases.json`** | 读 | 读 | 读 | **是 — 须 ADR**（`ADR-004` D1） |
| **`eval/eval_runner.py`** | 读 | 读 | 读 | **是 — 须 ADR**（`ADR-004` D1） |
| **`scripts/check_*.py`**（六道门禁检查器） | 读 | 读 | 读 | **是 — 须 ADR**（`ADR-004` D1） |
| **`scripts/fitness_functions.py`** | 读 | 读 | 读 | **是 — 须 ADR**（`ADR-004` D1） |
| **`scripts/mutation_check.py`** | 读 | 读 | 读 | **是 — 须 ADR**（`ADR-004` D1） |
| **`docs/code-governance/acceptance-coverage-map.yaml`** | 读/写 | 读 | 读 | **是 — 须 ADR**（`ADR-004` D1） |
| `test/offline/` | 读 | **无访问** | 读/写 | 否 |

> **`ADR-004` 引入的原则（D2）**：本项目有**两个平面** ——
> **运行平面**（`src/**`，决定系统做什么）与**验证平面**（`eval/**`、`scripts/**`、
> `data/*.json`、`docs/code-governance/**`、`docs/architecture/**`，决定**什么算正确**）。
> **两平面不得由同一方无约束地改动** —— 否则验证平面可被被测方调整以"通过"。
>
> **为什么验证资产的 BUILD 是 `Read` 而非 `No access`**：BUILD 需要**运行**评估与检查器
> 来自检（跑 `eval_runner` 看是否达标）。给读权限、封住"无 ADR 写"即可。
> 与 `src/compliance/` 的区别：合规层的**存在本身就是保证**，
> 而验证资产的**运行**是保证的一半。

**机器可读形式**：`.opencode/permissions.jsonc`（P-001~P-004、P-009、P-013~P-016）。
**变更触发拦截**：pre-commit hook（§4）。

---

## 4. 强制机制（enforcement）

课程行 599：**Permission 定义 WHO，Hook 强制 WHEN；两者都需要，单独任何一个都不够。**

| 机制 | 范围 | 本项目的实现 | 状态 |
|---|---|---|---|
| **Permission** | 宽范围、始终生效 | `.opencode/permissions.jsonc`（声明）+ 本文件（说明） | ✅ 本文件产出 |
| **Hook** | 事件特定（仅变更时） | `scripts/check_safety_paths.py`（CI 阶段） | ✅ 已实现并验证 |
| **CI 门禁** | 分支保护、合并前 | 6 道门禁（`.github/workflows/ci.yml`） | ✅ 已实现；**待管理员启用分支保护** |
| **Fitness function** | 结构约束、每次提交 | `scripts/fitness_functions.py`（S1/S2/S3、V1–V4） | ✅ 已实现 |

> ⚠️ **诚实的局限**（必须说清，否则本表是虚假承诺）：
> · **T1/T2（读工具）无法机械强制** —— 读取不产生副作用，CI 不可观测。
>   故 blindnes invariant 靠**角色纪律 + 审计**，不是靠拦截。本项目的缓解是：
>   BUILD 阶段的产出必须能追溯到已批准计划，且 `docs/ai-use-log.yaml` 记录每次会话的角色。
> · **Hook 的缺口**：目前 hook 只在 **CI** 生效，**本地 pre-commit 尚未安装**。
>   这意味着绕过路径存在（本地直接改 `data/*.json` 后提交，直到 CI 才被发现）。
>   补法见 `TD-026`。

---

## 5. 人工确认清单

| # | 待确认项 | 状态 |
|---|---|---|
| 1 | T18/T19（改依赖 / 改 CI）是否确需人工批准，还是可接受 agent 自行变更 | ⏳ **需你决定** |
| 2 | 是否安装本地 pre-commit hook（关闭 `TD-026` 的绕过路径） | ⏳ **待你执行** `python scripts/install_hooks.py` |
| 3 | ~~`eval/` 的权限级别~~ | ✅ **已由 `ADR-004` D1 解决**：纳入受保护路径，改动须 ADR |
| 4 | `ADR-004` D1 扩大了受保护面（9 → 19 条），是否需要收紧粒度 | ⏳ 见 `ADR-004` 的重开触发器 **T3** |

---

## 附：本文件的派生追溯

| 本文件章节 | Derived From | 来源工件 |
|---|---|---|
| §1 角色定义 | 角色约束表 | `AGENTS.md` ⑥；课程行 3683–3684、3660 |
| §2 工具清单 | 授权声明 | 本文档（课程未规定形式，按类别声明） |
| §3 路径授权 | safety-critical 清单 | `ADR-002` §2 D4 |
| §4 强制机制 | Permission + Hook 双机制 | 课程行 599；`ADR-002` §2 D4 |
| §5 人工清单 | 待决项 | `TD-025`、`TD-026` |
