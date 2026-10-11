# .opencode/rules.md —— 项目级 always-on 行为规则

> **⚠️ HUMAN-ONLY FILE**（课程 D3 明示）。
> 本文件约束编码 agent 的**常驻行为**，故**不得由被约束者自行修改** ——
> 机器访问级别为 `none`（见 `.opencode/permissions.jsonc` 的 P-010 规则）。
> 唯一有权修改的角色是 **HUMAN**。
>
> 课程对应：D3 第 5 项 —— *"the project-level always-on behavioral rules for the coding agent.
> Human-only file."*
> **状态**：草案待批（须人类批准）· 版本：V1 · 日期：2026-10-06
>
> **与 `AGENTS.md` 的分工**：`AGENTS.md` 是**读什么 / 能改什么 / 验什么**的规格入口；
> **本文件是每次会话都生效的行为约束** —— 无论任务是什么都适用。
> 二者不重复：`AGENTS.md` 因任务而异（读特定工件），本文件恒定。

---

## R1 —— 计划先于代码（最高优先级）

**在 `docs/plans/` 中提交执行计划清单并获人类明确批准之前，禁止输出源代码、修改文件或调用执行类工具。**

- 依据：课程行 3830（**MANDATE**）；`docs/execution-plan-template.md`；`Prompt.md` §2。
- 计划的五个部分不可省：**Traceability / Interface Contract / Scope Boundaries /
  Testing Strategy / Implementation Steps**。
- 若验证失败：**修订计划，不得跳到代码**。
- **计划是契约**：一经批准，不得偏离所声明的文件、导入与接口；需要变更时**重新出计划**。

> **本规则的历史记录（诚实声明）**：本项目在 P5/P6 曾**违反**本规则 ——
> 按人类"先跑通"的指示，测试与实现同批产出，计划未先行。
> 该违规未掩盖，登记为 **`TD-023`**，并在 P7 完成纠正（计划 → 批准 → 测试先获批 → 实现）。
> **本规则之所以被写死在 always-on 位置，正是因为它被违反过一次。**

## R2 —— 绝不为通过检查而改变判据

**禁止为让检查变绿而修改检查、放宽阈值、删除难例或跳过测试。**

- 依据：课程行 5183（架构工件 HUMAN ONLY）；`INV-ADS-011`；`TD-025`（评估集的同类漏洞）。
- 若检查失败，**唯一允许的动作是修实现或修架构**（见 R4）。
- 特别地：
  - 不得改 `docs/code-governance/acceptance-coverage-map.yaml` 的 `test_backed` 标记而不补真实证据；
  - 不得改 `eval/eval_cases.json` 的期望值以匹配当前行为（那是"把 bug 固化为正确答案"，见 `ADR-003` D7）；
  - 不得改 `.github/workflows/` 或检查器脚本来绕过失败的门禁。

## R3 —— 发现缺口必须登记，不得静默

**任何"做不到 / 没做 / 暂时这样"的地方，必须在 `docs/debt-register.md` 立条目并写明
补法与重开条件。**

- 依据：`INV-ADS-011`（缺口必须有去向）；`BUG-003` 的设计原则（不得凭空造 ID 或伪造空测试）。
- 覆盖表里 `test_backed: false` 的每条必须带 `pending_test` 与 `blocked_by`，二者缺一即 FAIL。
- 本项目的立场：**缺口可登记、不可掩盖**。历史缺口（`TD-018`、`TD-021`、`TD-023`）均保留在册。

## R4 —— 失败归因：行为失败 ⇒ 改架构，不改代码

**若行为测试失败而结构测试通过，正确动作是走 ADD-R 修订架构，不是 patch 代码。**

- 依据：`ADR-002` §2 D3；`INV-ADS-009`。
- 课程原话：*The code is CORRECT. The architecture is UNDERSPECIFIED.*
- 同理：若某条不变量"在设计中无法被强制"，**停止并修订架构**，不得降低不变量。

## R5 —— safety-critical 变更须 ADR + 人工批准

**改动下列路径前必须停止，产出 ADR，并取得人类批准。**

- 依据：`ADR-002` §2 D4；`INV-ADS-010`。
- 清单的**唯一来源**是 `ADR-002` D4（`scripts/check_safety_paths.py --show-paths` 可打印）。
  **不得在此重复列举** —— 两处列举必然漂移（`BUG-007` 的教训）。
- 提交信息中须**引用 ADR ID**（`check_safety_paths.py` 据此判定）。

## R6 —— 角色隔离（blindness invariants，不可协商）

- **BUILD 不得读取 `test/` 下任何测试文件。** 只接收 **stripped error report**
  （失败测试 ID + 断言摘要，不含测试实现）。
  - 理由：若 Build 能读测试，它会把测试改成匹配其破损实现 —— **测试通过、不变量被违反、无人察觉**。
- **TESTER 不得读取 `src/` 下任何实现文件。** 只依据 `requirements.yaml`、fit criteria 与
  接口契约（`AGENTS.md` ④⑤）。
- **VERIFY 不得修改代码、写 ADR 或改测试。**
- 详细授权见 `.opencode/permissions.jsonc` §1。

## R7 —— 绝不自批

**agent 不得批准自己的计划、测试、ADR 或豁免。**

- 依据：课程 §11.3 **No agent may self-approve**。
- 批准者必须是**具名人类**；`docs/test-approvals.yaml` 中 `approved_by` 为占位符的记录
  **不被采信**（`check_test_approval.py` 会拒绝）。
- 若某处需要人类决定而人类未表态：**停下来问**，不得代为决定。

## R8 —— 上下文新鲜度（context freshness）

**需求变更后，与本项目相关的规则须在**一个 sprint 内**同步更新。**

- 依据：课程 D3 对 `.agent/rules.md` 的 context freshness 要求（本文件同样适用）。
- 具体含义：`requirements.yaml` 变更后，须在一个 sprint 内检查并更新：
  `AGENTS.md` ④⑤、`structural-constraints.md`、本文件、`.opencode/permissions.jsonc`、
  `acceptance-coverage-map.yaml`。
- **反例（本项目真实发生过）**：P5/P6 落地后，`README.md` 仍写着"4 个为空目录"、
  `AGENTS.md` ① 仍写"剩余模块"、`architecture-blueprint.md` §4 仍标"P7 待建"。
  这些漂移已修正，但**它们证明了新鲜度不会自动维持**。
- **登记机制**：`TD-024`（模块表漂移）即为该规则被违反时留下的债。

## R9 —— 只读数据源与无状态

- **`data/*.json` 只读**；素材与规则的变更走人工入库流程，不在运行期改写。
- **审计只写不读**：决策路径**禁止回读**审计历史 —— 回读会引入隐藏状态，
  使同一输入在不同历史下产出不同决策（违反无状态设计，`memory-design.md` §2 S1）。
- **本项目的无状态是刻意的**：V1 不保存会话状态、不做检查点（`memory-design.md` §3）。

## R10 —— 报告要具体指标，不要"已加日志"

- 汇报 monitor 时须给出**具体指标名与阈值**（来源：`trace-matrix.md` §1 的 Runtime Monitor 列；
  登记册在 `src/audit/metrics.py`）。
- 依据：`TD-001`（22 条 monitor 的落地是本项目最重的债之一）。
- 反例：写"已添加监控"而无指标名 —— 该表述不可验证，等同于未做。

---

## 违规的处置

| 情形 | 处置 |
|---|---|
| 违反 R1（计划未批即写码） | 停止；补计划并登记债（先例：`TD-023`） |
| 违反 R2（改判据以通过） | **视为最严重违规** —— 因为它是**掩盖而非失败**；须立即回退并登记 |
| 违反 R3（静默跳过缺口） | 补登记；若已提交，回填 `debt-register.md` 与覆盖表 |
| 违反 R5（无 ADR 改 safety-critical） | CI **阻断**（`check_safety_paths.py`）；须补 ADR 或回退 |
| 违反 R6（角色越界读文件） | 技术不可拦；靠 `ai-use-log.yaml` 审计 + 人工评审发现 |
| 违反 R7（自批） | CI 阻断（占位符批准者不被采信）；须取得具名人类批准 |

> **本文件的权威性来自被遵守，而非被写下。**
> 故上表逐条给出**已发生的先例**或**已实现的强制手段** ——
> 无先例、无强制的规则应被质疑是否值得存在。

---

## 附：本文件的派生追溯

| 规则 | Derived From | 来源工件 |
|---|---|---|
| R1 计划先于代码 | MANDATE | 课程行 3830；`Prompt.md` §2 |
| R2 不得改判据 | 工件 HUMAN ONLY | 课程行 5183；`TD-025` |
| R3 缺口登记 | 验证完整性 | `INV-ADS-011`；`BUG-003` 原则 |
| R4 失败归因 | ADD-R | `ADR-002` D3；`INV-ADS-009` |
| R5 safety-critical | Permission + Hook | `ADR-002` D4；`INV-ADS-010` |
| R6 角色隔离 | blindness invariants | `AGENTS.md` ⑥；课程行 3683–3684 |
| R7 绝不自批 | No agent may self-approve | 课程 §11.3 |
| R8 上下文新鲜度 | context freshness | 课程 D3（`.agent/rules.md` 要求） |
| R9 只读与无状态 | 状态设计 | `memory-design.md` §2 S1、§3 |
| R10 具体指标 | monitor 登记 | `TD-001`；`trace-matrix.md` §1 |
