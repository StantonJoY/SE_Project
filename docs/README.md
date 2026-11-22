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
| 权威边界（AI 为什么不能决定展示） | [`architecture/adr-001-guarded-hybrid.md`](architecture/adr-001-guarded-hybrid.md) |
| 失败语义与治理 | [`architecture/adr-002-fail-closed-and-governance.md`](architecture/adr-002-fail-closed-and-governance.md) |
| V2 竞价为什么另起入口 | [`architecture/adr-005-v2-atomic-auction.md`](architecture/adr-005-v2-atomic-auction.md) |
| V3 语料边界与 5% 定价 | [`architecture/adr-006-v3-corpus-boundary.md`](architecture/adr-006-v3-corpus-boundary.md)（D1–D9） |
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
| agent 会话原始记录 | [`../transcripts/`](../transcripts/) |

---

## 维护规则

- 新增顶层文档或改文档目录结构时，**同时更新本索引**（否则等于没写）。
- 本索引不放状态数字（数字会过期），只放"去哪找"。
- 数字口径以 `docs/architecture/invariants.md`、`docs/req/requirements.yaml`、
  `docs/code-governance/acceptance-coverage-map.yaml` 三处为准。
