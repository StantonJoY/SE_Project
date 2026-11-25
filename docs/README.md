# 文档索引（Documentation Index）

> 45+ 份文档的入口。**按"我要做什么"查，不按目录查。**
> 同步日期：2026-11-22（V3 合入 `main` 后）

---

## 1. 第一次接手这个项目

| 想知道 | 读 |
|---|---|
| 系统现在能做什么、怎么跑 | [`HANDOVER-V3.md`](HANDOVER-V3.md)（当前版本） |
| 历史：V1 / V2 怎么演进的 | [`HANDOVER.md`](HANDOVER.md)、[`HANDOVER-V2.md`](HANDOVER-V2.md) |
| 编码 agent 的权限与红线 | [`../AGENTS.md`](../AGENTS.md) |
| 整体架构 | [`../architecture-blueprint.md`](../architecture-blueprint.md) |

## 2. 需求与验收

| 想知道 | 读 |
|---|---|
| 有哪些需求、怎么验证 | [`req/requirements.yaml`](req/requirements.yaml) |
| 需求 schema 与校验规则 | [`req/req-schema.json`](req/req-schema.json)、[`code-governance/acceptance-coverage-map.yaml`](code-governance/acceptance-coverage-map.yaml) |
| V3 需求草稿（含未采纳的 RAG 方案） | [`req/requirements-v3-se.md`](req/requirements-v3-se.md)、[`req/requirements-v3-rag-draft.md`](req/requirements-v3-rag-draft.md) |
| 不变量与 fallback | [`architecture/invariants.md`](architecture/invariants.md) |
| 验收状态（正式） | [`v2-approval-status.yaml`](v2-approval-status.yaml)、[`v3-approval-status.yaml`](v3-approval-status.yaml) |

## 3. 架构与决策

| 想知道 | 读 |
|---|---|
| 权威边界（AI 为什么不能决定展示） | [`architecture/adr/001-guarded-hybrid.md`](architecture/adr/001-guarded-hybrid.md) |
| 失败语义与治理 | [`architecture/adr/002-fail-closed-and-governance.md`](architecture/adr/002-fail-closed-and-governance.md) |
| V2 竞价为什么另起入口 | [`architecture/adr/005-v2-atomic-auction.md`](architecture/adr/005-v2-atomic-auction.md) |
| V3 语料边界与 5% 定价 | [`architecture/adr/006-v3-corpus-boundary.md`](architecture/adr/006-v3-corpus-boundary.md)（D1–D9） |
| 需求 → 组件 → 测试 → monitor | [`architecture/trace-matrix.md`](architecture/trace-matrix.md) |
| 上下文与记忆 | [`architecture/memory-design.md`](architecture/memory-design.md) |

## 4. 治理与流程

| 想知道 | 读 |
|---|---|
| 6 条结构约束 / 4 条验证约束 | [`code-governance/structural-constraints.md`](code-governance/structural-constraints.md)、[`code-governance/verification-constraints.md`](code-governance/verification-constraints.md) |
| 工具权限矩阵 | [`code-governance/mcp-tool-manifest.md`](code-governance/mcp-tool-manifest.md) |
| 测试批准记录 | [`test-approvals.yaml`](test-approvals.yaml) |
| AI 使用日志 | [`ai-use-log.yaml`](ai-use-log.yaml) |
| 分支保护怎么开 | [`branch-protection.md`](branch-protection.md)、[`../.github/CODEOWNERS`](../.github/CODEOWNERS) |
| 已知债务 | [`debt-register.md`](debt-register.md)（TD-001…028） |
| 踩过的坑 | [`bug-diary.md`](bug-diary.md)（BUG-001…008）、[`HANDOVER-V3.md`](HANDOVER-V3.md) §6 |

## 5. 测试与证据

| 想知道 | 读 |
|---|---|
| V3 测试做了什么、结论如何 | [`testing/V3-Test-Report.md`](testing/V3-Test-Report.md) |
| 逐条执行记录 | [`testing/V3-Test-Execution.md`](testing/V3-Test-Execution.md) |
| 真实模型提示词效果 | [`testing/V3-Live-Prompt-Semantic-Report.md`](testing/V3-Live-Prompt-Semantic-Report.md) |
| 演示脚本与截图 | [`testing/V3-Demo-Script.md`](testing/V3-Demo-Script.md)、[`testing/V3-Demo-Screenshots.md`](testing/V3-Demo-Screenshots.md) |
| 原始证据（junit / stdout / png） | [`../evidence/v3/`](../evidence/v3/) |
| 评审备忘 | [`review-memo.md`](review-memo.md) |
| 文档面一致性审查 | [`testing/V3-Documentation-Consistency-Audit.md`](testing/V3-Documentation-Consistency-Audit.md) |

## 6. 计划与历史

| 想知道 | 读 |
|---|---|
| 每一轮怎么排的计划 | [`plans/`](plans/) |
| 补监控（TD-001）的方案与步骤 | [`plans/TD-001-monitor-wiring.md`](plans/TD-001-monitor-wiring.md) |
| 还剩什么活、怎么分 | [`plans/REMAINING-WORK.md`](plans/REMAINING-WORK.md) |
| 报告（D6）的硬性要求与现状 | [`plans/REPORT-REQUIREMENTS.md`](plans/REPORT-REQUIREMENTS.md) |
| agent 会话原始记录 | [`../transcripts/`](../transcripts/) |

---

## 维护规则

- 新增顶层文档或改文档目录结构时，**同时更新本索引**（否则等于没写）。
- 本索引不放状态数字（数字会过期），只放"去哪找"。
- 数字口径以 `docs/architecture/invariants.md`、`docs/req/requirements.yaml`、
  `docs/code-governance/acceptance-coverage-map.yaml` 三处为准。
---

---

## 7. 文档全表

> 分类索引只列常用入口；这里是**全部文档**，保证没有"写了但没人知道在哪"的文件。
> 结构按课程第 5 节：`docs/architecture/adr/NNN-*.md`、`docs/code-governance/`、`docs/req/`。

| 文件 | 标题 |
|---|---|
| [`architecture/adr/001-guarded-hybrid.md`](architecture/adr/001-guarded-hybrid.md) | ADR-001：采用 Guarded Hybrid 架构（AI 解释，代码裁决） |
| [`architecture/adr/002-fail-closed-and-governance.md`](architecture/adr/002-fail-closed-and-governance.md) | ADR-002：Fail-Closed 终态、证据不可协商与失败归因治理 |
| [`architecture/adr/003-evaluation-set-as-architecture.md`](architecture/adr/003-evaluation-set-as-architecture.md) | ADR-003：评估集作为一等架构资产 —— 判定口径、分母分离与阈值语义 |
| [`architecture/adr/004-verification-plane-protection.md`](architecture/adr/004-verification-plane-protection.md) | ADR-004：评估与验证资产纳入受保护路径清单（ADR-002 D4 的补充） |
| [`architecture/adr/005-v2-atomic-auction.md`](architecture/adr/005-v2-atomic-auction.md) | ADR-005：V2 确定性竞价与原子预算结算 |
| [`architecture/adr/006-v3-corpus-boundary.md`](architecture/adr/006-v3-corpus-boundary.md) | ADR-006：V3 轮次接入与真实语料边界 |
| [`architecture/adr/007-requirements-prioritization.md`](architecture/adr/007-requirements-prioritization.md) | ADR-007：需求优先级（MoSCoW）与显式取舍记录 |
| [`architecture/adr/008-layered-context-and-assembly.md`](architecture/adr/008-layered-context-and-assembly.md) | ADR-008：分层上下文结构与装配流水线 |
| [`architecture/asr-register.md`](architecture/asr-register.md) | ASR 登记册（Architecturally Significant Requirements Register） |
| [`architecture/concern-clusters.md`](architecture/concern-clusters.md) | Concern Cluster（关注点聚类） |
| [`architecture/evaluation-logbook.md`](architecture/evaluation-logbook.md) | Evaluation Logbook — 架构选择的累积证据（D2.9，optional） |
| [`architecture/evaluation-table.md`](architecture/evaluation-table.md) | 候选方案评估表（Candidate Evaluation Table，D2 #8） |
| [`architecture/invariants.md`](architecture/invariants.md) | 不变量登记册（Invariant Register） |
| [`architecture/memory-design.md`](architecture/memory-design.md) | 记忆与状态设计说明（Memory / State Design Note） |
| [`architecture/option-ledger.md`](architecture/option-ledger.md) | Option Ledger — 被否决的架构选项与重开条件（D2.11，optional） |
| [`architecture/permission-model.md`](architecture/permission-model.md) | Permission Model — 角色级文件读写权限（D2.6） |
| [`architecture/risk-list.md`](architecture/risk-list.md) | Risk List — 假设、可能变成的缺陷与复核触发点（D2.10，optional） |
| [`architecture/runtime-policy-catalog.md`](architecture/runtime-policy-catalog.md) | 运行时策略目录（Runtime Policy Catalog） |
| [`architecture/trace-matrix.md`](architecture/trace-matrix.md) | 追踪矩阵（Trace Matrix） |
| [`branch-protection.md`](branch-protection.md) | 分支保护配置（Branch Protection）— D7 交付物 |
| [`bug-diary.md`](bug-diary.md) | 缺陷日记（Bug Diary） |
| [`code-governance/coverage-v1-summary-snapshot.md`](code-governance/coverage-v1-summary-snapshot.md) | V1 覆盖汇总历史原文 |
| [`code-governance/mcp-tool-manifest.md`](code-governance/mcp-tool-manifest.md) | MCP Tool Manifest —— 编码 agent 可调用的工具与角色授权（D3） |
| [`code-governance/structural-constraints.md`](code-governance/structural-constraints.md) | 结构性约束（Structural Constraints） |
| [`code-governance/verification-constraints.md`](code-governance/verification-constraints.md) | 验证约束（Verification Constraints） |
| [`debt-register.md`](debt-register.md) | 技术债登记册（Debt Register） |
| [`design/technical-design-v1.md`](design/technical-design-v1.md) | 场景化广告推荐引擎 — V1 技术实现方案 |
| [`execution-plan-template.md`](execution-plan-template.md) | 执行计划清单（Execution Plan Manifest）— 模板 |
| [`HANDOVER-V2.md`](HANDOVER-V2.md) | V1 → V2 交接文档（Handover to Next Developer） |
| [`HANDOVER-V3.md`](HANDOVER-V3.md) | V3 交付说明（Handover · 给测试同学） |
| [`HANDOVER.md`](HANDOVER.md) | CS5351 项目交接文档（HANDOVER） |
| [`plans/P4-selector.md`](plans/P4-selector.md) | 执行计划清单 · P4 — `src/selector/` AI 建议层 |
| [`plans/P7-eval.md`](plans/P7-eval.md) | 执行计划清单 · P7 — 固定评估集 + 版本溯源 + 变异验证 |
| [`plans/REMAINING-WORK.md`](plans/REMAINING-WORK.md) | 剩余工作清单（分配用） |
| [`plans/REPORT-REQUIREMENTS.md`](plans/REPORT-REQUIREMENTS.md) | 报告（D6）的硬性要求与现状对照 |
| [`plans/SUBMISSION-CHECKLIST.md`](plans/SUBMISSION-CHECKLIST.md) | 提交打包清单（ZIP） |
| [`plans/TD-001-monitor-wiring.md`](plans/TD-001-monitor-wiring.md) | TD-001 补监控方案（运行时 monitor 接线） |
| [`plans/V2-execution.md`](plans/V2-execution.md) | V2 执行计划与真实授权边界 |
| [`plans/V3-execution.md`](plans/V3-execution.md) | V3 执行计划（Execution Plan）· 真实语料接入 |
| [`req/requirements-v1-draft.md`](req/requirements-v1-draft.md) | 场景化广告推荐引擎 — V1 需求与功能点草案 |
| [`req/requirements-v2-bidding-draft.md`](req/requirements-v2-bidding-draft.md) | 场景化广告推荐引擎 — V2 候选需求：报价竞价框架 |
| [`req/requirements-v3-rag-draft.md`](req/requirements-v3-rag-draft.md) | 场景化广告推荐引擎 — V3 需求草案：检索增强（RAG）与真实语料 |
| [`req/requirements-v3-se.md`](req/requirements-v3-se.md) | V3 需求规格（正式稿）· 真实语料接入 |
| [`review-memo.md`](review-memo.md) | 评审备忘录（Review Memo） |
| [`testing/V1-Demo-Screenshots.md`](testing/V1-Demo-Screenshots.md) | CS5351 V1 Mock / Offline 截图演示 |
| [`testing/V1-Demo-Script.md`](testing/V1-Demo-Script.md) | CS5351 V1 Mock / Offline 截图演示 |
| [`testing/V1-Test-Execution.md`](testing/V1-Test-Execution.md) | V1 测试执行记录 |
| [`testing/V1-Test-Report.md`](testing/V1-Test-Report.md) | CS5351 V1 Mock / Offline 测试报告 |
| [`testing/V3-Demo-Screenshots.md`](testing/V3-Demo-Screenshots.md) | CS5351 V3 Screenshot Demo |
| [`testing/V3-Demo-Script.md`](testing/V3-Demo-Script.md) | CS5351 V3 Screenshot Demo Script |
| [`testing/V3-Documentation-Consistency-Audit.md`](testing/V3-Documentation-Consistency-Audit.md) | V3 文档一致性审查（Documentation Consistency Audit） |
| [`testing/V3-GitHub-Gate-Evidence.md`](testing/V3-GitHub-Gate-Evidence.md) | GitHub 门禁实证：三张图 + 文字说明 |
| [`testing/V3-Live-Prompt-Semantic-Report.md`](testing/V3-Live-Prompt-Semantic-Report.md) | V3 Live Prompt Semantic Quality Report |
| [`testing/V3-Test-Documents-README.md`](testing/V3-Test-Documents-README.md) | V3 测试文档索引 |
| [`testing/V3-Test-Execution.md`](testing/V3-Test-Execution.md) | V3 测试执行记录 |
| [`testing/V3-Test-Report.md`](testing/V3-Test-Report.md) | V3 阶段性测试报告 |
| [`testing/V3-V1-Live-Prompt-Semantic-Report.md`](testing/V3-V1-Live-Prompt-Semantic-Report.md) | V1 Live Prompt Semantic Quality Report |

## 8. 其他顶层工件

| 路径 | 作用 |
|---|---|
| [`../Prompt.md`](../Prompt.md) | 静态启动指令（D9） |
| [`../prompts/prompt_v1.0.yaml`](../prompts/prompt_v1.0.yaml) | V1 冻结运行时提示词（ctx-v1） |
| [`../prompts/prompt_v1.1.yaml`](../prompts/prompt_v1.1.yaml) | 现行运行时提示词（ctx-v1.1 + relevance-v2.2） |
| [`../AGENTS.md`](../AGENTS.md) | 编码 agent 治理入口（D3） |
| [`../architecture-blueprint.md`](../architecture-blueprint.md) | 主约束文档（D2.1） |
| [`../Report.md`](../Report.md) | 过程报告与自评（D6） |
