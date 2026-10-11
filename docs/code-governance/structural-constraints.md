# 结构性约束（Structural Constraints）

> **D3 交付物** · 课程对应：note 行 3686–3712（P181）、行 5387–5394
> **消费者**：BUILD agent（生成前）、VERIFICATION agent（生成后）、HUMAN REVIEWER（只复核 P0 违规）
> **状态**：草案待批 · 版本：V1（`docs/architecture/` 轮次）· 日期：2026-10-06
> **上游**：`architecture-blueprint.md`、`docs/architecture/adr-001/002-*.md`、`docs/architecture/invariants.md`
> **机械化实现**：`scripts/fitness_functions.py`（CI Tier 1 结构门，**独立于任何 LLM**）

> 课程关键原则（note 行 3753）：**结构约束管 ORGANIZATION，验证约束管 EVIDENCE。**
> 本文件只管"代码该长什么样"；"怎么证明它对"见 `verification-constraints.md`。

---

## 1. Module Organization —— 一个元素一个模块（S1）

**规则**：每个架构元素**恰好**映射到一个模块。一对一，可追溯。

来自 `architecture-blueprint.md` §4 的组件分解：

| 架构元素 | 模块 | 权威级别 | 对应需求 | 现状 |
|---|---|---|---|---|
| ① 素材契约 + 候选集构建 | `src/ads/` | Authority（数据准入） | `REQ-ADS-ARCH-001`、`FR-001` | ✅ |
| ② 场景输入契约 | `src/scene/` | Authority（输入准入） | `REQ-ADS-FR-002` | ✅ |
| ③ **FINAL AUTHORITY**（合规管道） | `src/compliance/` | **Authoritative** | `REQ-ADS-NFR-SAFETY-001`~`004` | ✅ |
| ④ AI 建议层（闭集选择 + 上下文 + 解释） | `src/selector/` | **Advisory only** | `REQ-ADS-ARCH-002/003`、`SEC-001`、`NFR-COST-001`、`AI-001` | ❌ P4 |
| ⑤ 输出契约 | `src/render/` | 表达 | `REQ-ADS-FR-004` | ❌ P6 |
| ⑥ 证据子系统 | `src/audit/` | Evidence only | `REQ-ADS-GOV-001`、`AI-002` | ❌ P6 |
| ⑦ 编排 / 降级路径 / CLI | `src/app/` | Orchestration | `REQ-ADS-FR-003`、`NFR-PERF-001` | ❌ P5 |

**禁止**：

- ❌ 一个文件里实现两个架构元素（例如把 `EventLog` 与 `ToolDispatcher` 写在同一个模块）。
- ❌ 新增未被上表登记的顶层包——**出现孤儿模块即为 S1 违规**（`fitness_functions.py` 会 FAIL）。
- ❌ 为一个元素建两个模块（职责重复）。

**包布局约束**：`pyproject.toml` 使用 `[tool.setuptools.packages.find] where=["src"]`，
因此 ①–⑦ 是**平级顶层包**。模块间一律**绝对导入**（`from compliance.pipeline import ...`），
**禁止相对跨包导入**（`from ..ads import ...`）。

---

## 2. Extension Never Replacement —— 扩展永不删除（S2）

**规则**：新的设计轮次**扩展**上一轮的代码基线，**永不删除、永不替换**。

课程对 build target 的冻结规则（note 行 3761–3767）：

| Build Target | 先前层 | 当前层 | 新层 |
|---|---|---|---|
| **V1 — Forward Build**（本轮） | — | `src/` **可修改** | — |
| **V2 — Forward Build**（`docs2/`，未启动） | `src/`（V1）**FROZEN / Read-only** | `src/bidding/` **可修改** | — |

**本轮（V1 forward build）的适用性说明**：`src/` 全部为本轮新增，**不存在"改动基线"的对象**，
因此 S2 的"永不替换"在**本轮无适用对象**。但 S2 的**实质要求**在本轮以另一种形式成立：

> **authority 边界不得被绕过**——这是 S2 的精神在本轮的检查形式。

**当前 authority 边界检查项**：

| 检查 | 期望 |
|---|---|
| `src/compliance/` 存在且承载唯一裁决 | ✅ 存在 |
| 不得存在绕过 compliance 直接展示的路径 | ✅ 当前无展示路径（P5 待建，届时必须复检） |
| `src/selector/`、`render/`、`audit/` 不得自行决定"展示或不展示" | ⏳ 待 P4/P6 建成后由 fitness function 强制 |

**V2 启动时的强制动作**：把 V1 层标为 `FROZEN`，并新增 CI 检查
`git diff <V1 冻结标签> -- src/` **必须为零行变更**（课程行 4142 的做法）。

---

## 3. Traceability —— ADR docstring 可追溯性（S3）

**规则**（课程行 3710）：每个元素的接口引用**约束它的 ADR 章节与 invariant**。

**两层要求**：

| 层级 | 要求 | 检查方式 |
|---|---|---|
| **模块级** | 每个 `src/**/*.py` 的模块 docstring **必须引用至少一条 ADR / REQ / INV ID** | `fitness_functions.py` 的 S3 检查（AST 解析 docstring，正则匹配 ID） |
| **函数级** | 每个实现架构元素的函数，其 docstring 引用它满足的 fit criterion | 人工评审 + 后续逐函数补检 |

**规定格式**：

```python
"""<模块一句话职责>。

Implements: ADR-001（Guarded Hybrid——AI 建议、代码裁决）
            ADR-002 D1（降级终态 no_ad，fail-closed）
Enforces: INV-ADS-001（未经确定性合规过滤的广告绝不被展示）
Verifies: REQ-ADS-NFR-SAFETY-001（零逃逸）
"""
```

当前 11 个 `src/` 模块已全部满足模块级要求（见 `fitness_functions.py` PASS）。

---

## 4. Authority Boundaries —— 权威边界

**规则**（课程行 5394）：**任何新代码都不得绕过强制元素。**

来自 `architecture-blueprint.md` §5 的权威分配，以下为**不可协商的边界**：

| # | 边界规则 | 强制不变量 | 现状 |
|---|---|---|---|
| **A1** | 不存在任何绕过 `compliance.run_compliance()` 直接展示广告的路径 | `INV-ADS-001` | ✅ 无展示路径 |
| **A2** | LLM 输出未经 `parse_llm_output()` schema 校验，不得进入管道 | `INV-ADS-003` | ⏳ P4 |
| **A3** | 展示的 `ad_id` 必须属于候选集（存在性 gate 不可省） | `INV-ADS-002` | ✅ 已实现 |
| **A4** | `src/selector/` 不得写 `ad_id` 之外的决策结果；不得写成交/花费字段（V2） | `INV-ADS-004` | ⏳ P4 |
| **A5** | 解释路径**只读**，绝不写决策变量（课程 INV-007 的对应物） | `INV-ADS-004` | ⏳ P4 |
| **A6** | `src/audit/` **只写不读**——决策路径不得回读审计历史 | `INV-ADS-012` | ⏳ P6 |
| **A7** | 审计写入失败 → 本次推荐整体失败（不静默继续） | `INV-ADS-012` | ⏳ P6 |
| **A8** | 任何需求变更不得删除既有测试（回归门） | `INV-ADS-011` | ✅ V4 已强制 |

> **P0 违规定义**（HUMAN REVIEWER 只处理这三类，课程行 5434）：
> **authority collapse**（权威崩塌）、**invariant failure**（不变量失败）、**scope violation**（范围越界）。
> 其余全部由 `fitness_functions.py` 与 pytest 自动判定，**无需人工读输出**（课程行 3931）。

---

## 5. 机械化检查清单（CI Tier 1）

`scripts/fitness_functions.py` 实现以下自动断言，**在 pre-merge CI 中运行，失败即拒绝构建**：

| 检查 | 对应约束 | 失败条件 |
|---|---|---|
| `src/` 包 ↔ 架构元素一对一 | S1 | 出现未登记的顶层包；或有实现但无任何需求 `enforcement` 指向它 |
| compliance 权威边界存在 | S2 / A1 | `src/compliance/` 缺失 |
| 模块 docstring 引用 ADR/REQ/INV | S3 | docstring 为空或不含任何 ID |
| 每条 fit criterion 有测试或已登记去向 | V1 | 见 `verification-constraints.md` §1 |
| 每条不变量有反例测试或已登记去向 | V2 | 见 `verification-constraints.md` §2 |
| 测试模块引用 REQ/INV | V3 | 模块 docstring 不含 ID |
| 既有测试模块未消失 | V4 | `test/offline/test_*.py` 缺失 |
| 追踪矩阵与注册表同步 | — | 某条基线需求未出现在 `trace-matrix.md` |

> 课程行 3914：`fitness-functions/` 由 `structural-constraints.md` **自动生成**；
> 本项目的对应实现是**一个脚本 + 一张覆盖映射表**（`docs/code-governance/acceptance-coverage-map.yaml`），
> 因为本项目规模无需目录化的函数集合。**映射是机械的**（课程行 3916），不靠人工判断。

---

## 6. 人工确认清单

| # | 待确认项 | 建议 | 状态 |
|---|---|---|---|
| 1 | §1 模块 ↔ 元素映射表 | 维持 | ⏳ 待批 |
| 2 | §2 本轮 S2 的适用性说明（无基线可改，改以 authority 边界检查替代） | 接受 | ⏳ 待批 |
| 3 | §4 的 A1~A8 边界规则 | 维持 | ⏳ 待批 |
| 4 | §5 的机械化检查项是否足够 | 维持；P4/P5/P6 建成后需扩充 | ⏳ 待批 |
