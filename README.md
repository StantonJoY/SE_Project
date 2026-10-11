# SE Project — 场景化广告推荐引擎（Ad Recommendation Engine）

CS5351 Agentic Software Engineering Project · 2026-2027

在人类监督下，用 AI coding agent 构建一个**场景化广告推荐引擎**：
给定广告素材库与用户场景特征（时段 / 设备 / 用户标签），系统选出一条广告并渲染展示。
核心命题：**AI 做推荐决策（LLM）+ 确定性代码做合规兜底** —— AI 是顾问，代码是执行官。

## 课程交付物状态（D1~D9）

| # | 交付物 | 状态 | 说明 |
|---|---|---|---|
| **D1** | 机器可读需求 + Schema | ✅ 完成 | `requirements.yaml`（22 基线 + 19 候选）+ `req-schema.json` + 双向一致性校验 |
| **D2** | 架构工件（11 类） | ✅ 完成 | 5 份 CORE（blueprint / invariants / trace-matrix / memory-design / ADR×2）全就位；另含 ASR 登记册、concern cluster、runtime-policy-catalog |
| **D3** | 编码治理 | ✅ **完成** | `AGENTS.md` + `structural-constraints.md` + **`mcp-tool-manifest.md`**（工具与角色授权）+ **`.opencode/permissions.jsonc`**（机器可读权限模型，含 guard rules 与 enforcement）+ **`.opencode/rules.md`**（R1–R10 常驻行为规则，human-only）+ **`.agent/rules.md`**（五项公约：抽象上限 / 依赖约束 / 测试独立性 / safety-critical 须 ADR / 上下文新鲜度） |
| **D4** | 验证治理 | ✅ 完成 | `verification-constraints.md`、`review-memo.md`、`debt-register.md`、`bug-diary.md` + Tier 1 fitness function |
| **D5** | Agent 会话记录 | ❌ **缺** | `transcripts/` 空。**原始"从零构建"记录不在本机**（现存会话最早为 2026-10-06）。**需团队提供** |
| **D6** | 报告 `Report.md` | ❌ **缺** | 需姓名/学号、相对贡献表、每人自评（300–500 词，**不能代写**）。**需团队提供** |
| **D7** | GitHub 仓库 + 6 道门禁 | ⚠️ 部分 | `ci.yml` + 6 个门禁检查器 + 分支保护文档已完成；**待人工执行**：分支保护设置、CODEOWNERS 账号、门禁 1 具名批准者 |
| **D8** | 源码与测试 | ✅ **完成** | **7 个架构元素全部实现**（ads / scene / compliance / selector / render / audit / app）；模块名与架构元素一致 ✅；测试布局 offline/live 分离 ✅（`test/live/` 待 P8 才有内容）。**285 个离线测试** + **13/13 变异验证** |
| **D9** | 静态 Prompt `Prompt.md` | ✅ 完成 | 启动指令 + 执行计划五要素模板（`docs/execution-plan-template.md`）；明确"停下来等人工批准" |
| — | **P7 评估与验证资产** | ✅ 完成 | `eval/` 固定评估集 **25 条** + replay runner（分母分离 / 违规零容忍，见 `ADR-003`）；`scripts/mutation_check.py` |

> **D8 的说明**：`src/` 已包含**课程硬性要求的真实 AI 组件** —— `src/selector/`
> （LLM 闭集选择 + 严格输出校验 + 六层上下文装配 + 解释路径隔离），
> 其上 `MockLLM` 提供确定性离线运行。`TD-020` 已关闭。
>
> **唯一未覆盖的需求**：`REQ-ADS-GOV-002`（权限模型 + pre-commit hook）—— 属 D3 的
> `.opencode` 交付物，**非 P8 范围**。

## 架构一句话

```
场景特征 ──→ 规则预筛候选集 ──→ LLM 闭集选择（advisory）
                                      ↓
                    compliance 五步确定性管道（FINAL AUTHORITY）
                    output_exists → banned_words → banned_check → category → scene
                                      ↓
                      APPROVE → 渲染 + 解释 ／ REJECT → no_ad + 原因码
                                      ↓
                              审计证据（恰好 1 条）
```

**权威边界**：LLM 只能从候选集内选择，不得自创广告；compliance 管道不可被任何路径绕过。
**失败语义**：本项目无运行时人类复核环节，故降级终态统一为 `no_ad`（fail-closed）。
设计依据见 `docs/architecture/adr-001-guarded-hybrid.md` 与 `adr-002-fail-closed-and-governance.md`。

## 版本演进

| 版本 | 内容 | 状态 |
|---|---|---|
| V1 | 规则预筛 → LLM 闭集选择 → 合规过滤 → 渲染（无 RAG、无竞价） | **基线**（`docs/architecture/` 轮次） |
| V2 | 报价竞价框架：LLM 降级为相关性建议，竞价引擎确定性定胜负 | 候选（归属 `docs2/` 轮次，未启动） |
| V3 | RAG 场景向量召回 | 占位 |

> 课程要求每轮 ADD **append-only 且绝不合并轮次**：V1 工件在 `docs/architecture/`，
> V2 启动时新建 `docs2/architecture/`，并将 V1 层标为 FROZEN。

## 阻塞门禁设计（课程 D7 · §6）

课程要求 CI/CD 实装 **6 道阻塞门禁**。本仓库的实现与**当前真实状态**如下 ——
受限项**显式声明，不伪装为已完全满足**：

| # | 门禁（课程原文） | 实现 | 状态 |
|---|---|---|---|
| **1** | **Test approval** — 变更的测试须在实现开始前获批 | `scripts/check_test_approval.py` + `docs/test-approvals.yaml` | ⚠️ **机制就绪，待首次真实批准**；历史提交无法追溯满足（见下） |
| **2** | **Static analysis** — lint / 类型 / 依赖检查每次提交；安全路径 PR 另跑 contract / security / API-surface / permission 检查 | `ruff` + `mypy` + `scripts/check_dependencies.py` + `scripts/check_safety_paths.py` + `scripts/fitness_functions.py` | ✅ 已实装 |
| **3** | **Schema** — 需求注册表须通过其 JSON Schema | `scripts/validate_requirements.py`（schema + 一致性 + 架构输入双向校验） | ✅ 已实装 |
| **4** | **Semantic evaluation** — prompt/model 变更须先 replay 固定评估集过阈值 | `scripts/check_semantic_eval.py` | ⚠️ **受限**：固定评估集未建（口径待 OQ-005），且当前无 prompt 文件。脚本对"有 prompt 变更但无评估集"**阻断（fail-closed）** |
| **5** | **Regression** — 每次变更跑全部历史测试套件 | `pytest test/offline` + `scripts/audit_implementation.py` | ✅ 已实装（86 个测试） |
| **6** | **AI-use log** — 改代码或 prompt 未更新 AI-use 日志即阻塞 | `scripts/check_ai_use_log.py` + `docs/ai-use-log.yaml` | ✅ 已实装 |

**分支保护**（课程 §6）：`main` 要求 6 个 status check 全通过 + ≥1 名人工评审；
**安全关键路径的改动必须附带架构决策** —— 由 `check_safety_paths.py`
从 `adr-002` §2 D4 **以及** `adr-004` D1 **解析**受保护路径清单（共 **19 条**，
不硬编码，避免与 ADR 漂移），若变更触及"须 ADR"路径而无 ADR 引用则阻断。
完整配置步骤与 `gh` 命令见 **`docs/branch-protection.md`**。

### 门禁的生效起点与历史缺口（诚实声明）

6 道门禁于 **2026-10-06** 设计并落地。此前的 4 次构建提交（`edac673` / `3ea7868` /
`d85f910` / `d097d34`，2026-09-30）**未经任何门禁直接进入 `main`**，且其中测试与实现
同批产出，因此 **门禁 1 的历史要求无法追溯满足**。该缺口：

- 登记于 `docs/debt-register.md`（`TD-016`）与 `docs/ai-use-log.yaml`（`AIU-0002`~`AIU-0004`）；
- 在 `docs/branch-protection.md` §6 与前文显式声明；
- 作为 **D6 报告的过程质量证据**保留（"发现治理顺序错了并补回"是真实的过程事实）。

## 文档索引

| 文档 | 路径 | 说明 |
|---|---|---|
| **V1 需求注册表（机器可读）** | `docs/req/requirements.yaml` | **D1 唯一需求单一来源**，语义化 ID + fit criterion + ASR 判定 |
| **需求 JSON Schema** | `docs/req/req-schema.json` | 门禁 3 校验用 |
| 需求校验器 | `scripts/validate_requirements.py` | Schema + 一致性 + 架构输入双向校验 |
| V1 需求底稿（informative） | `docs/req/requirements-v1-draft.md` | 内容底稿，冲突时以注册表为准 |
| V2 竞价候选需求（candidate） | `docs/req/requirements-v2-bidding-draft.md` | 归属 `docs2/` 轮次 |
| V1 技术实现方案 | `docs/design/technical-design-v1.md` | 模块划分、实施顺序 P0~P8 |
| **ASR 登记册（A1）** | `docs/architecture/asr-register.md` | 18 ASR + 4 impl；五维 Litmus 判定 |
| **不变量登记册（A2）** | `docs/architecture/invariants.md` | 16 条不变量，六字段，fallback 全 fail-closed |
| concern cluster（A5） | `docs/architecture/concern-clusters.md` | 5 簇 + 优先级 + 冲突裁决 + 假设 |
| 架构蓝图（CORE） | `architecture-blueprint.md` | **仓库根目录**，11 节可执行约束 |
| 追踪矩阵（CORE） | `docs/architecture/trace-matrix.md` | 需求 → 组件 → 测试 → **运行时 monitor** |
| 记忆/状态设计（CORE） | `docs/architecture/memory-design.md` | V1 无状态的论证与后果 |
| ADR | `docs/architecture/adr-001..004-*.md` | ①Guarded Hybrid ②fail-closed 与治理 ③评估集为一等架构资产 ④**验证平面保护** |
| 运行时策略目录 | `docs/architecture/runtime-policy-catalog.md` | 17 条失败策略（`RP-001`~`017`） |
| 编码代理治理入口 | `AGENTS.md` | 由架构工件装配而成（非散文撰写） |
| 结构/验证约束 | `docs/code-governance/` | S1–S3、V1–V4、三层验证、角色分离 |
| 验收覆盖映射 | `docs/code-governance/acceptance-coverage-map.yaml` | 每条 REQ/INV 的测试证据或待补去向 |
| 技术债登记 | `docs/debt-register.md` | 按课程 AI-era 八类分类 |
| 缺陷日记 | `docs/bug-diary.md` | 症状/复现/根因/修复/**暴露的不变量缺口** |
| 评审备忘录 | `docs/review-memo.md` | 规格/架构/代码测试质量/操作元数据 → 判定 |
| 分支保护配置 | `docs/branch-protection.md` | 要设什么 + `gh` 命令 + 生效起点声明 |
| AI 使用日志 | `docs/ai-use-log.yaml` | 门禁 6 的载体 |
| 测试批准记录 | `docs/test-approvals.yaml` | 门禁 1 的载体 |
| 交接文档 | `docs/HANDOVER.md` | **新对话开场先读** |
| **静态启动 prompt（D9）** | `Prompt.md` | 仓库根目录；启动指令 + 人工批准闸门 |
| 执行计划模板 | `docs/execution-plan-template.md` | 五要素清单（Traceability / Interface / Scope / Testing / Steps） |

## 如何运行

### 离线测试（不调 LLM，确定性）

```bash
pip install -e ".[dev]"
pytest test/offline -q
```

### 全部门禁（本地等价于 CI）

```bash
ruff check src test scripts                              # 门禁 2 · lint
mypy                                                     # 门禁 2 · 类型
python scripts/check_dependencies.py                     # 门禁 2 · 依赖
python scripts/check_safety_paths.py --base origin/main   # 门禁 2 · 安全路径 + ADR
python scripts/fitness_functions.py                      # Tier 1 · 架构 fitness function
python scripts/validate_requirements.py                  # 门禁 3 · Schema
pytest test/offline -q                                   # 门禁 5 · 回归
python scripts/audit_implementation.py                   # 实现 ↔ 需求一致性审计
python scripts/check_ai_use_log.py --base origin/main     # 门禁 6 · AI-use 日志
python scripts/check_test_approval.py --base origin/main  # 门禁 1 · 测试批准
python scripts/check_semantic_eval.py --base origin/main  # 门禁 4 · 语义评估
```

### live 测试（需真实 LLM API）

尚未建立（`test/live/` 为空，P8 待做；供应商选型见 `OQ-001`）。

## 目录结构

```
SE_Project/
├── README.md                    # 本文件
├── AGENTS.md                    # D3 编码代理治理入口（由架构工件装配）
├── architecture-blueprint.md    # D2 CORE · 主约束文档（课程要求位于根目录）
├── Prompt.md                    # D9 静态启动 prompt
├── Report.md                    # D6 报告（**待建**，需团队成员信息）
├── config.yaml                  # 配置单一来源（阈值 / 超时 / 路径 / 评估门阈值）
├── pyproject.toml               # 依赖 + ruff/mypy/pytest/depcheck 配置
├── .github/workflows/ci.yml     # D7 · 6 道阻塞门禁 + fitness + 变异验证
├── data/                        # 素材 / 违禁词 / 场景规则（safety-critical）
├── src/                         # **7 个架构元素全部实现**
│   ├── ads/                     # ① 素材契约 + 候选集构建
│   ├── scene/                   # ② 场景输入契约
│   ├── compliance/              # ③ FINAL AUTHORITY（五步纯函数管道）
│   ├── selector/                # ④ AI 建议层（闭集选择 + 上下文装配 + 解释）
│   ├── render/                  # ⑤ 输出契约（两形态判别联合 schema）
│   ├── audit/                   # ⑥ 证据子系统（JSONL + 22 条 monitor 登记册）
│   └── app/                     # ⑦ 编排 / CLI / 注入门 / 降级路径
├── test/
│   ├── offline/                 # 确定性测试（15 个模块，285 个测试）
│   └── live/                    # 依赖 API 的测试（**待 P8**，无真实 LLM 时不放假测试）
├── eval/                        # ⑧ **固定评估集（25 条）+ replay runner**（门禁 4）
│   └── reports/                 # replay 报告（append-only）
├── prompts/                     # 版本化运行时 prompt（**待 P8**）
├── scripts/                     # ⑨ 校验器、六道门禁检查器、审计器、变异验证、演示
├── transcripts/                 # D5 agent 会话记录（**待团队提供**）
└── docs/
    ├── HANDOVER.md              # 交接文档
    ├── req/                     # D1 需求（注册表 + Schema + 底稿）
    ├── architecture/            # D2 架构工件（ASR/不变量/追踪/记忆/ADR×4/策略/簇）
    ├── code-governance/         # D3/D4 结构约束、验证约束、验收覆盖映射
    ├── plans/                   # 执行计划清单（P4 / P7）
    ├── design/                  # 设计草案
    ├── execution-plan-template.md  # D9 五要素模板
    ├── ai-use-log.yaml          # 门禁 6 载体
    ├── test-approvals.yaml      # 门禁 1 载体
    ├── branch-protection.md     # 分支保护配置
    ├── review-memo.md           # 评审备忘录
    ├── debt-register.md         # 技术债登记（TD-001~025）
    └── bug-diary.md             # 缺陷日记
```
