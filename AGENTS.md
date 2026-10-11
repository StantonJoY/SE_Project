# AGENTS.md — 编码代理治理入口

> **D3 交付物** · 课程对应：note 行 3755–3799（P182–183）、行 5405–5414
> **本文件由 SA 规格装配而成，不是以散文形式撰写**（课程行 3789）。
> **每一节都追溯到一个架构工件**——没有任何内容是凭空发明的（课程行 3773、3787）。
> **状态**：草案待批 · 版本：V1（`docs/architecture/` 轮次）· 日期：2026-10-06

> **给编码代理的第一条指令**：读本文件及它引用的全部工件，**在写任何代码之前**。
> 按课程行 3830：**在执行计划清单获得明确人工批准之前，严格禁止输出源代码、修改文件或调用执行类工具。**
> 跳过 blueprint 的代理会产出违反架构边界的代码（课程行 1432）。

---

## ① Build Target（构建目标）

**V1 场景化广告推荐引擎的 7 个架构元素已全部落地并可端到端跑通；本轮（P7）补齐评估与验证资产。**

| 项 | 值 |
|---|---|
| 构建目标 | V1（`docs/architecture/` 轮次） |
| 已有实现 | `src/ads/`、`src/scene/`、`src/compliance/`（**已完成，见 ③ 的保护规则**） |
| 已建实现 | `src/selector/`（P4）、`src/app/`（P5）、`src/render/` + `src/audit/`（P6）—— **7 个元素全部落地，系统可端到端跑通** |
| 待建 | `eval/`（P7：固定评估集 + replay）、`scripts/mutation_check.py`（P7：变异验证） |
| 不构建 | V2 竞价（`docs2/` 轮次，未启动）；V3 RAG |

**来源**：`architecture-blueprint.md` §1 Scope；`docs/req/requirements.yaml` 的 `evolution_rounds`。

**交付完成的判据**（来源：`docs/architecture/trace-matrix.md` §1 的 Status 列）：
`REQ-ADS-FR-003`、`FR-004`、`ARCH-003`、`NFR-SAFETY-005`、`SEC-001`、`NFR-PERF-001`、
`NFR-COST-001`、`NFR-QA-001`、`GOV-001`、`GOV-002`、`AI-001`、`AI-002` 的 Status 由
`design` 转为 `tested`。

---

## ② Artifact Reading Order（工件阅读顺序）

**必须按此顺序读完，然后才生成任何代码。** 后读的层在取代先读的层之处**具有权威性**。

| 顺序 | 工件 | 读它的理由 |
|---|---|---|
| 1 | `docs/req/requirements.yaml` | 需求单一来源；ID、fit criterion、`enforced_by` |
| 2 | `docs/architecture/asr-register.md` | 哪些需求强制结构决策（A1）；18 ASR + 4 impl |
| 3 | `docs/architecture/invariants.md` | **16 条不变量 + fallback**；不可协商的边界 |
| 4 | `docs/architecture/adr-001-guarded-hybrid.md` | **权威边界**：谁决策、谁检查、谁必须不行动 |
| 5 | `docs/architecture/adr-002-fail-closed-and-governance.md` | 失败语义、证据不可协商、权限+hook |
| 6 | `architecture-blueprint.md` | 主约束文档：11 节（权威、工作流、权限、验证、可观测、变更策略） |
| 7 | `docs/architecture/trace-matrix.md` | 每条需求的强制组件 + 测试证据 + **运行时 monitor** |
| 8 | `docs/architecture/memory-design.md` | 状态与保留策略（V1 无状态，但**上下文装配受它约束**） |
| 9 | `docs/architecture/concern-clusters.md` | 5 个 concern cluster 与优先级（用于权衡取舍） |
| 10 | `docs/architecture/runtime-policy-catalog.md` | **16 条失败策略**（`RP-001`~`016`）——实现降级路径的直接依据 |
| 11 | `docs/code-governance/structural-constraints.md` | S1/S2/S3 + A1–A8 权威边界 |
| 12 | `docs/code-governance/verification-constraints.md` | V1–V4 + 测试位置 + 三层验证 |
| 13 | `docs/code-governance/acceptance-coverage-map.yaml` | 每条 REQ/INV 的测试证据与待补去向 |

**来源**：`architecture-blueprint.md` §2 Drivers；课程行 5410。

---

## ③ Code Baseline Scope（代码基线：可读 / 可修改 / 冻结）

| 路径 | 权限 | 依据 |
|---|---|---|
| `src/ads/`、`src/scene/` | **Read-only**（实现已冻结） | `structural-constraints.md` §1；`REQ-ADS-ARCH-001`、`FR-002` 已 `tested` |
| `src/compliance/` | **Read-only，改动须 ADR + 人工批准** | `ADR-002` §2 D4 safety-critical 清单；`INV-ADS-001` |
| `data/*.json` | **Read-only，改动须 ADR + 人工批准** | `ADR-002` §2 D4；`INV-ADS-007`、`008` |
| `docs/req/requirements.yaml` | **Read-only**（需求变更须 ADR） | `INV-ADS-010` |
| `docs/architecture/invariants.md` | **Read-only** | `ADR-002` §2 D4；课程行 5183（HUMAN ONLY） |
| `src/selector/`、`src/render/`、`src/audit/`、`src/app/` | **Modifiable（新建）** | 本轮 NEW 层 |
| `src/selector/context.py`、`src/app/pipeline.py` | **Modifiable（增量）** | P7 仅新增常量与审计字段（纯增量，不改既有签名/语义） |
| `eval/` | **Modifiable（新建）** | P7 NEW 层；**运行时决策路径之外**（只读验证资产） |
| `test/offline/` | **Modifiable** | `verification-constraints.md` §5 |

**禁止**：

- ❌ 不得修改 `src/ads/`、`src/scene/`、`src/compliance/` 的任何文件。
- ❌ 不得修改 `data/` 下任何 JSON。
- ❌ 不得删除或跳过任何既有测试（`INV-ADS-011`；`fitness_functions.py` 的 V4 检查会 FAIL）。
- ❌ 不得新建未在 ④ 登记的顶层包（S1 检查会 FAIL；`eval/` 已于 2026-10-06 登记）。

**来源**：`architecture-blueprint.md` §7 Permissions；`ADR-002` §2 D4。

---

## ④ Module Organization（模块组织表）

**源自 `architecture-blueprint.md` §4 的元素分解。每个架构元素恰好映射一个模块（S1）。**

| Module | 实现 | Pattern / ADR | Imports From |
|---|---|---|---|
| `src/selector/client.py` | `LLMClient` 协议 + `MockLLM` | ADR-001（AI 为 advisory） | 无先前层导入 |
| `src/selector/parser.py` | `parse_llm_output()` | ADR-001 §2（严格 JSON gate）· `INV-ADS-003` | `jsonschema` |
| `src/selector/context.py` | `route_budget()` + 六层装配 | `ASR-ADS-A3-01` · `INV-ADS-014` | `config.yaml` |
| `src/selector/explanation.py` | 解释路径（与决策路径分离） | `ASR-ADS-A3-02` · `INV-ADS-004` | `selector/parser.py` |
| `src/app/pipeline.py` | `recommend()` 编排 + fallback（**10 条降级路径**） | ADR-002 D1 · `INV-ADS-013` | `ads`、`scene`、`selector`、`compliance`、`render`、`audit` |
| `src/app/sanitize.py` | 输入 sanitize gate（**pre-model**；检出即拒绝） | `ASR-ADS-12` · `INV-ADS-005` | 无先前层导入 |
| `src/app/cli.py` | `argparse` 入口 | — | `app/pipeline.py` |
| `src/app/config.py` | 配置加载 + **启动期校验**（FAIL LOUDLY） | `ADR-002` §2 D4 · `memory-design.md` §3 S3 | `yaml` |
| `src/app/__main__.py` | `python -m app` 入口（纯转发，无逻辑） | `REQ-ADS-FR-003` | `app/cli.py` |
| `src/render/schema.py` | 输出契约（两形态判别联合 schema） | `REQ-ADS-FR-004` | 无先前层导入 |
| `src/render/serializer.py` | 结果序列化 | `REQ-ADS-FR-004` | `render/schema.py` |
| `src/audit/store.py` | JSONL 追加写（**只写不读**；恰好 1 条） | ADR-002 D2 · `INV-ADS-012` | 无先前层导入 |
| `src/audit/metrics.py` | 运行时 monitor 登记册（22 条） | `trace-matrix.md` §1 monitor 列 | `audit/store.py` |
| `eval/eval_cases.json` | **固定评估集**（数据资产，≥20 条） | `ASR-ADS-15` · `REQ-ADS-NFR-QA-001` | — |
| `eval/eval_runner.py` | 一键 replay + 通过率/违规数/p95 报告 | `ASR-ADS-15` · `ASR-ADS-11` | `app/pipeline.py`、`render`、`audit` |
| `scripts/mutation_check.py` | 变异验证（证明测试具备证伪能力） | `ASR-ADS-16` · `INV-ADS-011` | `pytest` |

**禁止**：一个文件实现两个元素；为一个元素建两个模块。

> **`src/app/` 有 5 个文件的说明**（原 `TD-024`，2026-10-06 已关闭）：
> `config.py` 与 `__main__.py` 是 `pipeline` / `cli` 两个元素的**支撑文件**，不各自构成独立元素。
> 在此登记以消除"文档 vs 实现"的漂移。
>
> **`eval/` 与 `scripts/` 的说明**：二者**不在 `src/` 下**，不参与 S1 的"元素↔模块"计数
> （S1 的范围是 `SRC = ROOT / "src"`）。它们在 `architecture-blueprint.md` §4 的 ⑧⑨ 中登记，
> 且**处于运行时决策路径之外** —— 只读、只报告，不参与"是否展示"的裁决。

**来源**：`architecture-blueprint.md` §4；`docs/architecture/trace-matrix.md`（monitor 列）；
`docs/architecture/runtime-policy-catalog.md`。

---

## ⑤ Interface Contracts（集成契约表）

**违反集成契约 = 架构违规**（课程行 3824）。顺序与保证均不可协商。

| Caller | Callee | 时点 | 契约 | 依据 |
|---|---|---|---|---|
| `app.sanitize` | `selector.client` | LLM 调用 **之前** | 注入模式必须先中和；未中和不得抵达模型 | `INV-ADS-005` |
| `app.pipeline` | `selector.context.assemble` | LLM 调用 **之前** | 六层上下文按预算装配；超 **85%** 触发 compaction | `INV-ADS-014`、`RP-010` |
| `selector.context` | （自身） | compaction **之后** | **必须重新注入层 2 的 standing constraints** | `INV-ADS-014`、`RP-010` |
| `app.pipeline` | `selector.parser.parse_llm_output` | LLM 返回 **之后** | 严格 JSON + schema 校验；失败重试 1 次 → 否则 `no_ad` | `INV-ADS-003`、`RP-004` |
| `app.pipeline` | `compliance.run_compliance` | **任何展示之前** | **五步**管道（含 `banned_check` 状态门）；任一失败即 REJECT → `no_ad` | `INV-ADS-001`、`INV-ADS-002` |
| `app.pipeline` | `selector.explanation` | 决策 **之后** | 解释路径**只读**；**绝不能写 `ad_id`**；解释失败不改决策 | `INV-ADS-004`、`RP-012` |
| `app.pipeline` | `audit.store.append` | 请求结束时 | **恰好 1 条**；含模式/候选规模/LLM 原始输出/过滤结果/最终输出/版本 | `INV-ADS-012`、`REQ-ADS-GOV-001` |
| **任何元素** | `audit.store.read` | — | **决策路径禁止回读审计历史**（回读会引入隐藏状态） | `memory-design.md` §2 S1 |
| `app.pipeline` | `render.serializer` | 决策定型后 | 两形态输出均须通过 render schema | `REQ-ADS-FR-004` |

**注意顺序**：`compliance` 必须在 LLM **之后**（它是 AI 之后的确定性强制层）。
**绝不允许**把 compliance 或 timeout 逻辑塞进 `selector/`——那会破坏 `concern-clusters.md` §0 的簇分离。

**来源**：`ADR-001` §2；`ADR-002` §2；`architecture-blueprint.md` §5；`runtime-policy-catalog.md`。

---

## ⑥ Verification Requirements（验证要求）

**代码提交前必须满足全部条件。** 执行命令（仓库根目录）：

```powershell
.\.venv\Scripts\python.exe scripts\validate_requirements.py   # Schema 门（D1）
.\.venv\Scripts\python.exe scripts\fitness_functions.py       # Tier 1 结构门
.\.venv\Scripts\python.exe -m pytest test/offline             # Tier 2 回归门
```

| # | 要求 | 依据 |
|---|---|---|
| 1 | 三层验证按序执行，**不跳层、不跨层并行**；任一层失败即停止 | 课程行 3903 |
| 2 | Tier 1 必须 PASS（检测"运行时 monitor"列） | 课程行 3903 |
| 3 | Tier 2：全部离线测试通过，**零回归** | `INV-ADS-011`、V4 |
| 4 | Tier 3：评估集 replay 达质量阈值，合规逃逸数 = 0 | `INV-ADS-016`、`INV-ADS-001` |
| 5 | **每条新需求的新增实现必须有测试**，且测试 docstring **引用它验证的 REQ/INV ID** | V1、V3 |
| 6 | **每条不变量必须有至少一个"会失败"的反例测试** | V2 |
| 7 | 每个新模块 docstring 必须引用 ADR 章节 + REQ/INV ID | S3 |
| 8 | **`src/ads/`、`src/scene/`、`src/compliance/` 下没有任何文件被修改** | S2、A1 |
| 9 | **测试不得使用 pytest `tmp_path`**（受限沙箱下子进程无法建临时目录）；用 I/O 边界打桩替代 | `verification-constraints.md` §5、`BUG-001` |
| 10 | 汇报 monitor 的具体指标名（来自 `trace-matrix.md` §1 的 Runtime Monitor 列），而非"已加日志" | `TD-001` |
| 11 | 不得为通过校验而伪造空测试或凭空造 ID；未覆盖项须在 `acceptance-coverage-map.yaml` 登记去向与阻塞原因 | `BUG-003` 的设计原则 |
| 12 | 若行为测试失败而结构测试通过 → **改架构（ADD-R），不要 patch 代码** | `ADR-002` §2 D3、`INV-ADS-009` |

**角色约束**（课程行 3683–3684、3660）：

| 角色 | 可读 | 可写 | **不得访问** |
|---|---|---|---|
| **BUILD**（本文件的主要读者） | ①–⑥ 工件、AGENTS.md、**stripped error report** | `src/selector/`、`render/`、`audit/`、`app/` | **`test/` 下任何测试文件** |
| **VERIFY** | 全部 | 仅合规报告 | 修改代码、写 ADR、改测试 |
| **TESTER** | `requirements.yaml`、fit criteria、接口契约（即本文件 ④⑤） | `test/` | **`src/` 下任何实现文件** |

> **blindness invariant ①（不可协商）**：**BUILD 不得读测试源码。**
> 理由：若 Build 能读测试，它会把测试改成匹配其破损实现——测试通过、不变量被违反、无人察觉。
> Build 只接收 **stripped error report**：失败测试 ID + 断言摘要，不含测试实现细节。

**来源**：`docs/code-governance/verification-constraints.md`；课程行 3846–3903。

---

## ⑦ 变更策略（何时必须停下来找人类）

| 触发 | 必须动作 |
|---|---|
| 需要修改 `src/compliance/`、`data/*.json`、`requirements.yaml`、`invariants.md` | **停止**，产出 ADR，取得人工批准（`INV-ADS-010`） |
| 发现某条不变量在设计中无法被强制 | **停止**，走 ADD-R 修订架构（`INV-ADS-009`） |
| 需要新增顶层包或改变模块职责边界 | **停止**，先更新 `architecture-blueprint.md` §4 与 ④ 表 |
| 需要放宽任何合规 gate 以提升出广告率 | **禁止**——`concern-clusters.md` §3 裁决第 6 条 |
| 需要引入"重试后展示次优候选"（使 `INV-ADS-003` 变为 fail-open） | **停止**，重开 `ADR-001` 触发器 T2 |
| 需求基线冻结（7 步循环 Step 1） | 需先人工批准 ADR-001/002 并关闭 `OQ-004`、`OQ-009` |

**来源**：`ADR-001` §6、`ADR-002` §6、`concern-clusters.md` §3、`architecture-blueprint.md` §10。

---

## 附：本文件的派生追溯（课程行 3775）

| 本文件章节 | Derived From | 来源工件 |
|---|---|---|
| ① Build Target | design round layering | `requirements.yaml` 的 `evolution_rounds`；`trace-matrix.md` |
| ② Reading Order | 工件依赖顺序 | 课程行 1543–1562 目录树 |
| ③ Code Baseline Scope | scope table | `ADR-002` D4；`blueprint.md` §7 |
| ④ Module Organization | 元素分解 | `blueprint.md` §4 |
| ⑤ Interface Contracts | ADR wiring + 不变量 | `ADR-001` §2、`ADR-002` §2、`runtime-policy-catalog.md` |
| ⑥ Verification Requirements | 治理约束 + 测试布局 | `verification-constraints.md` + `invariants.md` + fit criteria |
| ⑦ 变更策略 | re-open triggers | `ADR-001` §6、`ADR-002` §6 |

**本文件不是散文——每一条都引用了一个 ADR 章节、一个不变量 ID 或一条结构约束。**
