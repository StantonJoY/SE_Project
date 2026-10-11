# 架构蓝图（Architecture Blueprint）

> **CORE 工件（Agent Constraint）** · 课程对应：note 行 1412–1432（P59）、行 1545
> **定位**：本文件不是文档，而是**可执行的约束（executable constraint）**——把它注入每个编码代理会话，
> 代理在生成代码**之前必须先读**（note 行 1414、1432）。
> **状态**：草案待批 · 版本：V1（`docs/architecture/` 轮次）· 日期：2026-10-06
> **课程位置要求**：`architecture-blueprint.md` 必须位于**仓库根目录**（note 行 1545、课程 §5 目录树）。

> **三层决定权**（note 行 1573–1580）：
> **WHAT** = 架构（ADR-001/002）决定 · **WHERE** = `AGENTS.md` 决定哪个文件 · **HOW** = 编码代理决定类还是函数。
> 本蓝图提供 WHAT 与 WHERE 的约束边界。

---

## 1. Scope（范围）

**构建目标**：V1 场景化广告推荐引擎——给定场景特征与本地广告素材库，选出一条广告并渲染结构化结果。

| 在范围内 | 不在范围内（`requirements.yaml` scope.out） |
|---|---|
| 本地 JSON 素材库加载与校验 | RAG / 向量检索（V3） |
| 场景输入校验（时段/设备/用户标签） | 真实广告投放平台 / 实时竞价（V3+） |
| LLM 闭集选择（候选集内） | LLM 自由生成文案（V3） |
| 确定性合规过滤（**五步**纯函数管道） | 用户画像 / 多轮上下文记忆（V3） |
| 审计日志（JSONL，恰好 1 条/请求） | Web 前端界面（V3） |
| 降级为 `no_ad` 的失败路径 | 运行时人工复核队列（见 ADR-001 A3） |

**V2（`docs2/` 轮次，未启动）**：报价竞价框架。启动时本目录层标为 FROZEN。

---

## 2. Drivers（架构驱动因子）

按优先级（沿用课程 §3.7 姿态：Safety/Invariants > Deterministic Authority > Evidence > Selection > Cost）：

| # | 驱动因子 | 来源 ASR | 来源 REQ |
|---|---|---|---|
| D1 | **合规零逃逸**（核心） | `ASR-ADS-04` | `REQ-ADS-NFR-SAFETY-001` |
| D2 | 闭集选择（AI 非最终权威） | `ASR-ADS-02` | `REQ-ADS-ARCH-002` |
| D3 | 输出必须 schema 化 | `ASR-ADS-03` | `REQ-ADS-ARCH-003` |
| D4 | 敏感品类与违禁词拦截 | `ASR-ADS-05`、`06` | `REQ-ADS-NFR-SAFETY-002`、`003` |
| D5 | 场景硬约束双层防护 | `ASR-ADS-07` | `REQ-ADS-NFR-SAFETY-004` |
| D6 | 注入前置中和 | `ASR-ADS-12` | `REQ-ADS-SEC-001` |
| D7 | 降级不崩溃、终态 `no_ad` | `ASR-ADS-09`、`11` | `REQ-ADS-FR-003`、`NFR-PERF-001` |
| D8 | 证据完整可追溯 | `ASR-ADS-10`、`A3-03` | `REQ-ADS-GOV-001`、`AI-002` |
| D9 | 权限 + hook 变更治理 | `ASR-ADS-13` | `REQ-ADS-GOV-002` |
| D10 | 上下文预算与压缩后重注入 | `ASR-ADS-14`、`A3-01` | `REQ-ADS-NFR-COST-001` |
| D11 | 解释路径隔离 | `ASR-ADS-A3-02` | `REQ-ADS-AI-001` |
| D12 | 评估与验证门 | `ASR-ADS-15`、`16` | `REQ-ADS-NFR-QA-001`、`002` |

---

## 3. Boundaries（边界）

**系统边界**：单进程 CLI；无数据库（JSON 文件 + JSONL 日志）；唯一运行时第三方依赖 `jsonschema`。

**权威边界**（来自 ADR-001）：

```
┌─ 建议域（advisory）───────────┐   ┌─ 权威域（authoritative）────────────┐
│ LLM 闭集选择                   │   │ compliance 五步纯函数管道            │
│ 解释生成（reason）             │→ │ 阈值 gate / 超时 gate                │
│ 相关性判断                     │   │ 降级决策（no_ad）                    │
│ ✗ 不得自创广告                 │   │ 审计写入                             │
│ ✗ 不得输出候选集外 ID          │   │ ✓ 唯一可决定"展示或不展示"的元素      │
│ ✗ 不得写成交/花费（V2）        │   │ ✗ 不得被任何路径绕过                 │
└───────────────────────────────┘   └─────────────────────────────────────┘
```

**绝对边界**（违反即架构违规）：
1. 不存在任何绕过 compliance 管道直接展示广告的路径。
2. 不存在 LLM 输出未经 schema 校验即进入管道的路径。
3. 不存在未经审计的展示决策。

---

## 4. Components（组件分解）

模块 ↔ 架构元素**一一对应**（课程结构约束 S1：一个元素一个模块）。

| # | 模块 | 架构元素角色 | 权威级别 | 对应 REQ | 现状 |
|---|---|---|---|---|---|
| ① | `src/ads/` | 素材契约 + 候选集构建（`AdRepository`） | Authority（数据准入） | `ARCH-001`、`FR-001` | ✅ 已实现（P1） |
| ② | `src/scene/` | 场景输入契约（`parse_scene`） | Authority（输入准入） | `FR-002` | ✅ 已实现（P3） |
| ③ | `src/compliance/` | **FINAL AUTHORITY**（**五步**纯函数管道） | **Authoritative** | `NFR-SAFETY-001~004`、`ARCH-001` | ✅ 已实现（P2） |
| ④ | `src/selector/` | **AI 建议层**（闭集选择 + 上下文装配 + 解释） | **Advisory only** | `ARCH-002`、`003`、`SEC-001`、`NFR-COST-001`、`AI-001` | ✅ 已实现（P4） |
| ⑤ | `src/render/` | 输出契约（两形态） | 表达 | `FR-004` | ✅ 已实现（P6） |
| ⑥ | `src/audit/` | 证据子系统（JSONL + monitor 登记册） | Evidence only（不得改决策） | `GOV-001`、`AI-002` | ✅ 已实现（P6） |
| ⑦ | `src/app/` | 编排：pipeline + CLI + 降级路径 + 注入门 | Orchestration | `FR-003`、`NFR-PERF-001`、`SEC-001` | ✅ 已实现（P5） |

**⑧ 非 `src/` 的支持性构件**（不参与 S1 的"元素↔模块"计数——S1 仅扫描 `src/`）：

| # | 路径 | 角色 | 权威级别 | 对应 REQ | 现状 |
|---|---|---|---|---|---|
| ⑧ | `eval/` | **固定评估集（25 条）+ replay runner**（CI 阻断门） | 只读验证资产（不参与运行时决策） | `NFR-QA-001`、`NFR-PERF-001` | ✅ 已实现（P7） |
| ⑨ | `scripts/` | 治理检查器（schema / fitness / 门禁 1·2·4·6 / 审计 / **变异验证**） | 只读验证工具 | `NFR-QA-002`、`GOV-002` | ✅ 已实现（变异验证 13/13 检出） |

> **⑧⑨ 的登记理由**：`AGENTS.md` ⑦ 要求"新增顶层包须先更新 blueprint §4 与 ④ 表"。
> `eval/` 是 P7 新增的顶层包，故在此显式登记其角色与权威级别。
> 二者**处于运行时的决策路径之外** —— 评估集与检查器只读、只报告，不参与"是否展示"的裁决。
> **S1 检查的范围说明**：`fitness_functions.py` 的 `SRC = ROOT / "src"`，
> 故 ⑧⑨ 不受"一个元素一个模块"约束；但它们的**存在**在此有据可查（消除文档与实现的漂移）。

**包布局约束**（ADR 遗留决策）：`pyproject.toml` 用 `[tool.setuptools.packages.find] where=["src"]`，
因此 ①–⑦ 是**平级顶层包**；模块间一律**绝对导入**（`from compliance.pipeline import ...`），**禁止相对跨包导入**。
`eval/` 与 `scripts/` 不在 `src/` 下，**不参与打包**，只作为开发/CI 资产存在。

---

## 5. Authority（权威分配）

回答课程四问（note 行 1296–1302）：**谁决策 / 谁检查 / 谁记忆 / 谁**必须不**行动**。

| 元素 | Responsibility | Authority | **Forbidden From** | Governing Invariant |
|---|---|---|---|---|
| `AdRepository.load()` | 素材加载 + schema 校验 | 数据准入 | 跳过不合规素材 | `INV-ADS-015` |
| `AdRepository.filter_by_scene()` | 构建候选集（第一层场景剔除） | 候选准入 | 放行违反场景约束的素材 | `INV-ADS-008` |
| `parse_scene()` | 场景输入校验与规范化 | 输入准入 | 让非法输入进入 LLM | `INV-ADS-015` 族 |
| sanitize gate（`app`） | pre-model 注入中和 | Check gate | 解读输入、做选择 | `INV-ADS-005` |
| `selector`（LLM） | 建议 `ad_id` + `reason` + `confidence` | **Advisory only** | **自创广告、输出集外 ID、决定展示、写成交字段** | `INV-ADS-002`、`003`、`004` |
| 解释路径（`selector`） | 生成 `reason` | Explanation only | **影响决策结果、绕过 compliance** | `INV-ADS-004` |
| 阈值 gate（`app`） | 低置信度拦截 | Gate | 放行低于阈值的输出 | `INV-ADS-006` |
| timeout gate（`app`） | 超时拦截 | Gate | 长时间阻塞 | `INV-ADS-013` |
| `compliance.run_compliance()` | **确定性合规强制** | **FINAL AUTHORITY** | **被任何路径绕过** | `INV-ADS-001` |
| `audit` | 记录证据 | Logging only | **修改状态、改变决策** | `INV-ADS-012` |
| `pre_write_hook` | 拦截无 ADR 的 safety-critical 变更 | Enforcement | 放行无 ADR 的安全变更 | `INV-ADS-009`、`010` |

> **责任地图自检**（note 行 1322）：是否有责任未被分配？是否有责任被不必要地重复？
> 本项目：**无未分配责任**；compliance 与 selector 各有一组互不重叠的 forbidden actions。

---

## 6. Workflow（工作流：Plan / Build / Verify / Test 分离）

课程要求**没有任何单一 agent 可以 plan、build 并 verify**（note 行 3641），并有两条**blindness invariants**（行 3683–3684）。

| 角色 | Reads | Writes | **Must Not Access** | Blindness Invariant |
|---|---|---|---|---|
| **PLAN** | `docs/architecture/`、`docs/req/requirements.yaml` | 计划清单（Execution Plan Manifest） | 写任何实现代码 | 只解读架构，永不触碰实现层 |
| **BUILD** | `architecture-blueprint.md`、`AGENTS.md`、**stripped error report only** | `src/`（在 scope 内） | **`test/`（任何测试文件）**、ADR、invariants | ① **BUILD MUST NOT read test source** |
| **VERIFY** | `src/`、`test/`、specs | 仅 compliance report | 修改代码、写 ADR、改测试 | 只读，只报告发现 |
| **TESTER** | `docs/req/requirements.yaml`、fit criteria、接口契约 | `test/` | **`src/`（任何实现文件）** | ② **TESTER MUST NOT read implementation source** |

**理由**：若 Build 能读测试，它会把测试改成匹配其破损实现（测试通过、不变量被违反、无人察觉）；
若 Tester 能读实现，测试会描述实现而非规格，实现一改测试即失效。

**Plan-Before-Act**（课程行 3830）：在执行计划清单获得**明确人工批准**之前，**严格禁止输出源代码或修改文件**。

---

## 7. Permissions（文件级访问）

见 `adr-002-fail-closed-and-governance.md` §2 D4 的 safety-critical 路径清单。
机器可读形式待建：`.opencode/permissions.jsonc`（D3 交付物）。
**强制机制**：Permission（WHO，始终强制）+ pre-commit hook（WHEN，事件触发），**两者都需要**。

---

## 8. Verification（验证策略）

**三层验证，带门 CI，不得跳层**（课程行 3895–3903）：

| Tier | 检查内容 | 工具 | 门 |
|---|---|---|---|
| **Tier 1 — Structure** | 导入图、文件边界、模块 ↔ 元素一一对应 | `ast` / import-linter | PASS 才跑 Tier 2；FAIL 停止 |
| **Tier 2 — Correctness** | 全部测试通过、不变量强制、零回归 | `pytest` | PASS 才跑 Tier 3；FAIL 停止 |
| **Tier 3 — Behavior** | LLM 输出满足质量阈值、评估集 replay、零逃逸 | 评估 runner | PASS 才允许合并；FAIL 人工复核 |

**验证约束**（课程 §9.3）：
- V1：`requirements.yaml` 中**每条 fit criterion ≥ 1 个测试**。
- V2：**每条不变量 ≥ 1 个会失败的测试**（变异验证）。
- V3：每个测试引用其验证的 REQ / INV ID。
- V4：跨设计轮次**无回归**（上一轮全部测试必须继续通过）。

**当前状态**：Tier 2 部分建立（59 个离线测试）；Tier 1、Tier 3 未建立。

---

## 9. Observability（可观测性）

| 观测项 | 内容 | 对应不变量 | 现状 |
|---|---|---|---|
| 审计记录 | 场景 / 候选集规模 / LLM 原始输出 / 过滤结果 / 最终输出 / 降级原因码 | `INV-ADS-012` | 待建（P6） |
| 版本溯源 | `model_version` + `prompt_version` + `threshold` | `INV-ADS-012` | 待建 |
| 合规逃逸计数 | `compliance_escape_count` **必须恒为 0** | `INV-ADS-001` | 待建 |
| p95 延迟 | 端到端延迟 + SLA drift alert | `INV-ADS-013` | 待建 |
| 降级原因码分布 | 各 fallback 路径命中次数 | `INV-ADS-013` | 待建 |
| token 计数 | 每次请求上下文 token + compaction 次数 | `INV-ADS-014` | 待建 |

> **架构必须要求**：监控项**具体可度量**（课程行 5152）；"缺运行时 monitor → 无法发现生产故障"（行 5162）。

---

## 10. Change Policy（变更策略）

| 变更类型 | 流程 |
|---|---|
| 普通 `src/`（非 safety-critical） | PR + 测试 + 人工评审 |
| **safety-critical 路径**（§7 清单） | **必须 ADR + 人工批准 + hook 拦截** |
| compliance 规则（`data/*.json`） | 安全关键路径 → ADR + 人工批准 |
| 架构工件新增 | **Append-only**：只追加更高 ID 新条目，**从不擦除**（课程行 1583） |
| 替换架构元素 | 旧条目标 `status: OBSOLETED` + `replaced_by` 指针，**绝不物理删除**（课程行 4637） |
| 测试失败归因 | **遵守 ADR-002 D3**：结构测试通过而行为测试失败 → **改架构（ADD-R），不要 patch 代码** |

**ADR 重开触发器**：见 `adr-001-*.md` §6 与 `adr-002-*.md` §6，全部为可度量形式。

> **架构债务不得静默**（课程行 5246）：任何捷径或偏离必须记入 `docs/debt-register.md` 并带重开条件。

---

## 11. Filesystem（项目目录）

```
SE_Project/
├── README.md                      # 项目介绍
├── AGENTS.md                      # D3 编码代理治理入口（待建，由本蓝图派生，非散文撰写）
├── architecture-blueprint.md      # 本文件（课程要求位于根目录）
├── Prompt.md                      # D9 静态启动 prompt（待建）
├── Report.md                      # D6 报告（待建）
├── config.yaml                    # 配置单一来源（阈值、超时、路径）
├── pyproject.toml
├── data/                          # ads / banned_words / scene_rules（safety-critical）
├── src/                           # ads / scene / compliance / selector / render / audit / app
├── test/
│   ├── offline/                   # 确定性测试（不调 LLM）
│   └── live/                      # 依赖 API 的测试（待建）
├── eval/                          # eval_cases.json + eval_runner.py（待建）
├── prompts/                       # 版本化运行时 prompt（待建）
├── scripts/                       # validate_requirements.py、demo_p1.py
├── transcripts/                   # D5 agent 会话记录（待建）
└── docs/
    ├── HANDOVER.md
    ├── req/                       # D1：requirements.yaml + req-schema.json
    ├── architecture/              # D2：asr-register / invariants / adr-001 / adr-002（本文件在根）
    ├── code-governance/           # D3/D4：structural / verification / mcp-manifest（待建）
    ├── design/                    # technical-design-v1.md（其架构性内容正迁往 architecture/）
    ├── review-memo.md             # D4（待建）
    ├── debt-register.md           # D4（待建）
    └── bug-diary.md               # D4（待建）
```

**轮次目录规则**（课程行 1531/1562）：`docs/architecture/` = V1 轮次；V2 启动时新建 `docs2/architecture/`，
**V1 层冻结（IMMUTABLE）**，新条目只追加到 `docs2/`。**绝不合并不同轮次。**

---

## 12. 人工确认清单

| # | 待确认项 | 状态 |
|---|---|---|
| 1 | ADR-001 的候选与准则打分（C1/C2/C3） | ⏳ 待批 |
| 2 | §5 权威分配表（特别是 selector 的 forbidden actions） | ⏳ 待批 |
| 3 | §7 safety-critical 路径清单是否完整 | ⏳ 待批 |
| 4 | ADR-002 D1（`no_ad` 为终态）与 D2（审计失败即整体失败） | ⏳ 待批 |

> 本蓝图状态为**草案**。按课程行 3830，**计划获批前不得产出实现代码**。
