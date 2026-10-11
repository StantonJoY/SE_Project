# 验证约束（Verification Constraints）

> **D4 交付物** · 课程对应：note 行 3713–3740（P181）、行 5396–5403、行 3895–3903（三层验证）
> **消费者**：BUILD agent（提交前）、VERIFICATION agent（合规检查）、HUMAN REVIEWER（门）
> **状态**：草案待批 · 版本：V1（`docs/architecture/` 轮次）· 日期：2026-10-06
> **上游**：`docs/req/requirements.yaml`、`docs/architecture/invariants.md`、`docs/architecture/trace-matrix.md`
> **机械化实现**：`scripts/fitness_functions.py` + `docs/code-governance/acceptance-coverage-map.yaml`

> 分工（课程行 3753）：结构约束管 **ORGANIZATION**（见 `structural-constraints.md`），
> 本文件管 **EVIDENCE**——"怎么证明它对"。

---

## 0. 当前验证状况（诚实基线）

| 项 | 数值 |
|---|---|
| 离线测试 | **66 个，全部通过**（0 error） |
| 测试模块 | 4（`test_ads.py`、`test_scene.py`、`test_compliance.py`、`test_requirements_registry.py`） |
| 需求有测试证据 | **9 / 22** |
| 不变量有反例测试 | **5 / 16** |
| Tier 1 结构性检查 | ✅ 已建立（`fitness_functions.py`） |
| Tier 2 回归 | ✅ 已建立（pytest 全量通过） |
| Tier 3 行为/质量 | ❌ 未建立（评估集待建） |

**未覆盖的 13 条需求与 11 条不变量已逐条登记去向**，见 `acceptance-coverage-map.yaml`。
**不伪造测试**：标 `test_backed: false` 的条目就是没有测试，并有明确的阻塞原因。

---

## 1. V1 —— Fit Criterion Coverage（每条 fit criterion ≥ 1 个测试）

**规则**（课程行 3715、5400）：`requirements.yaml` 中**每条** fit criterion 至少有一个测试。
**没有测试就等于没有证据**表明该准则被满足。每个测试在 docstring 中引用自己的 fit criterion。

**落地方式**：以 `docs/code-governance/acceptance-coverage-map.yaml` 为**机器可读覆盖映射**。
`fitness_functions.py` 强制以下**双向自洽**：

| 断言 | 失败条件 |
|---|---|
| 覆盖表必须包含**全部** 22 条基线需求 | 缺条目即 FAIL |
| 声明 `test_backed: true` 的需求，其 ID 必须**真的出现在**某个测试模块中 | 映射与事实不符 → FAIL |
| 声明 `test_backed: false` 的需求，必须给出 `pending_test`（去向）与 `blocked_by`（阻塞原因） | 缺任一项即 FAIL |

> **为什么用覆盖表而不是"直接断言每条需求都有测试"**：
> 直接断言会在 P4~P6 未实现时**永久 FAIL**，从而诱使人伪造空测试。
> 覆盖表把"未覆盖"变成**必须显式登记的状态**——缺测试可以，**隐瞒缺测试不行**。
> 这是本项目的设计选择，理由记录于此以便审计。

**当前：9 / 22 有证据，13 条已登记去向。**

---

## 2. V2 —— Invariant Coverage（每条不变量 ≥ 1 个会失败的测试）

**规则**（课程行 3719、5401）：每条不变量至少要有一个**会失败的**测试。
测试必须在违反不变量时失败——**永远通过的测试什么也证明不了**。

**落地方式**：覆盖表的 `negative_test_backed` 字段 + **反例标记**双重验证：

| 断言 | 失败条件 |
|---|---|
| 覆盖表必须包含 `invariants.md` 声明的**全部** 16 条不变量 | 缺条目即 FAIL |
| 声明 `negative_test_backed: true` 的不变量，其 ID 必须出现在某个**含反例标记**的测试模块中 | 无反例标记 → FAIL（防止把"顺带提到"当成"反例测试"） |
| 声明 `false` 的必须给出 `pending_test` 与 `blocked_by` | 缺任一项即 FAIL |

**反例标记**（`fitness_functions.py` 识别的字样）：`反例`、`negative test`、`must fail`、`会失败`。

**当前：5 / 16 有反例测试。** 已有反例测试的不变量：
`INV-ADS-015`（素材契约）、`INV-ADS-001`（合规强制）、`INV-ADS-002`（集外拒绝）、
`INV-ADS-007`（品类与违禁词）、`INV-ADS-008`（场景双层）。

> **待补的重点**：三条**流程不变量**（`INV-ADS-009`/`010`/`011`）目前**都没有反例测试**。
> 课程标注流程不变量 **Required for full marks**（note 行 5122），因此这是优先级最高的补测项。

---

## 3. V3 —— Test Traceability（测试引用 invariant / REQ ID）

**规则**（课程行 3730）：每个测试在其 docstring 中引用它验证的 invariant 或 REQ ID。

**落地方式**：两层检查

| 层级 | 要求 | 检查方式 | 现状 |
|---|---|---|---|
| **模块级** | 每个测试模块的 docstring 必须含至少一个 REQ/INV/ADR ID | AST 解析 + 正则（`fitness_functions.py`） | ✅ 4/4 通过 |
| **函数级** | 每个测试函数的 docstring 引用其验证的 ID | 人工评审（部分模块已达标） | ⚠️ 部分——`test_ads.py`/`test_scene.py`/`test_compliance.py` 已逐函数标注；`test_requirements_registry.py` 仅模块级 |

> **已知缺口**：`test_requirements_registry.py` 的 35 个测试函数尚未逐一标注 docstring。
> 其模块级 docstring 已引用 `REQ-ADS-NFR-QA-002` 与 `INV-ADS-011`，故不违反模块级检查，
> 但**函数级未达标** → 登记为 `TD-010`。

---

## 4. V4 —— Regression（跨设计轮次无回归）

**规则**（课程行 3738、5402）：每个新的设计轮次都要跑此前**所有**轮次的测试套件。**全部必须通过。**

**落地方式**：

| 机制 | 实现 |
|---|---|
| 测试执行 | `pytest test/offline`（全量，不按轮次筛选——本项目单轮，目录即全集） |
| 测试模块不得消失 | `fitness_functions.py` 的 V4 检查：`REQUIRED_TEST_MODULES` 中的模块缺失即 FAIL |
| 测试不得被删除或跳过 | 人工评审 + PR diff 检查（课程 DoD 第 2 条：PR ≤ 5 文件 / 200 行） |
| V2 轮次启动时 | 追加 `git diff <V1 冻结标签> -- src/` 必须为零行变更 |

**当前：66 个测试全部通过，4 个模块齐全。**

---

## 5. 测试位置与命名（Test Location）

**规则**（课程行 5403）：测试与实现分层存放；**每个测试模块对应一个架构元素**。

| 测试模块 | 对应架构元素 | 测试数 |
|---|---|---|
| `test/offline/test_ads.py` | ① 素材契约 + 候选集构建 | 16 |
| `test/offline/test_scene.py` | ② 场景输入契约 | 8 |
| `test/offline/test_compliance.py` | ③ 合规管道（FINAL AUTHORITY） | 12 |
| `test/offline/test_requirements_registry.py` | 治理工件（D1 注册表 + 架构输入一致性） | 30 |
| `test/live/`（待建） | 依赖真实 LLM 的冒烟测试 | 0 |

**布局规则**：
- `test/offline/` = **确定性测试**，一律用 `MockLLM`，**不调真实 API**（ADR-005 原则）。
- `test/live/` = 依赖 API 的测试，标记 `live`，**不进默认 CI 门**。
- 命名：`test_<架构元素>.py`，与 `src/<element>/` 一一对应。

**沙箱兼容性约束（本项目特有，需保留）**：
测试**不得使用 pytest `tmp_path`**。原因：受限沙箱下子进程无法在子目录创建临时目录，
曾导致 5 个测试以 `PermissionError` 报错。替代做法是**在文件 I/O 边界打桩**
（`test_ads.py` 的 `_FakePath` + `monkeypatch.setattr(builtins, "open", ...)` 即范例）。

---

## 6. 三层验证与 CI 门（课程行 3895–3903）

| Tier | 检查内容 | 工具 | 门 | 现状 |
|---|---|---|---|---|
| **Tier 1 — Structure** | 导入图、文件边界、模块 ↔ 元素一一对应、docstring 可追溯性 | `ast` + `fitness_functions.py` | PASS 才跑 Tier 2；FAIL 停止 | ✅ 已建立 |
| **Tier 2 — Correctness** | 全部测试通过、不变量强制、零回归 | `pytest` | PASS 才跑 Tier 3；FAIL 停止 | ✅ 已建立 |
| **Tier 3 — Behavior** | LLM 输出满足质量阈值、评估集 replay、零逃逸 | 评估 runner | PASS 才允许合并 | ❌ 未建立 |

> **硬性规则**（课程行 3903）：**Tier 1 必须先于 Tier 2；Tier 2 必须先于 Tier 3。任何一层失败即停止流水线。
> 不跳层，不跨层并行。**

**执行命令**（仓库根目录）：

```powershell
.\.venv\Scripts\python.exe scripts\validate_requirements.py   # Schema 门（D1）
.\.venv\Scripts\python.exe scripts\fitness_functions.py       # Tier 1 结构门
.\.venv\Scripts\python.exe -m pytest test/offline             # Tier 2 回归门
```

---

## 7. 角色分离与 blindness invariants（课程行 3646–3684）

三条**不可协商**的盲区不变量在本项目中的落地：

| # | 盲区不变量 | 本项目落地 |
|---|---|---|
| **①** | **BUILD MUST NOT read test source** | Build agent 只接收 **stripped error report**（失败测试 ID + 断言摘要），**不得读 `test/` 目录**。理由：防止 agent 把测试改成匹配其破损实现 |
| **②** | **TESTER MUST NOT read implementation source** | Tester agent 只读 `requirements.yaml`、fit criteria 与接口契约，**不得读 `src/`**。理由：测试必须验证规格、描述实现 |
| **③** | 没有任何单一 agent 可以 plan + build + verify | 四角色分离见 `architecture-blueprint.md` §6 |

> **本项目的额外考量**：本会话中 AI 助手同时参与了需求撰写与测试撰写。
> 这**违反角色分离的精神**，已作为治理债登记为 `TD-011`，需在正式 CI 建立时由不同 agent/人承担。

---

## 8. 人工确认清单

| # | 待确认项 | 建议 | 状态 |
|---|---|---|---|
| 1 | §0 诚实基线（9/22 需求、5/16 不变量有证据） | 接受；不伪造测试 | ⏳ 待批 |
| 2 | §1 用覆盖映射表实现 V1 的设计选择 | 接受（避免诱使伪造空测试） | ⏳ 待批 |
| 3 | §5 "测试不得使用 tmp_path"作为项目约束 | 接受（沙箱兼容） | ⏳ 待批 |
| 4 | §7 角色分离当前未满足（同一 AI 兼任）→ `TD-011` | 接受为已知债务 | ⏳ 待批 |
| 5 | §0 Tier 3 未建立 | 接受；评估集落地后补齐 | ⏳ 待批 |
