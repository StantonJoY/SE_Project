# V2 阶段性测试报告

> 报告状态：PASS WITH LIMITATIONS
> 课程交付准备度：CHANGES REQUIRED
> Run ID：`v2-20261118-e1711d6-01`
> 测试日期：2026-11-18
> 证据目录：`evidence/v2/v2-20261118-e1711d6-01/`

## 1. 报告范围

本报告覆盖 V2 确定性竞价、预算结算、幂等、事务、安全边界、审计、固定评估、V1 回归及离线端到端演示。

本次还覆盖 Live smoke、拒绝路径、幂等、20 次 p95 以及 token/成本估算。

仍不包含：

- human-labeled live semantic quality
- 完整可重复 live quality suite
- 真实支付或曝光确认
- 远程 CI 和分支保护的实际运行证据

## 2. 测试基线

| 项目 | 值 |
|---|---|
| 测试分支 | `test/v2-validation` |
| 来源分支 | `origin/feat/v2-agent-workflow` |
| 测试代码 Commit | `e1711d641077ad9be29ad44bde1580d5d8b219d5` |
| 证据快照 Commit | `00fc22d0aa6587258e25c8fddbe3996bb36dd81f` |
| 基线 Commit | `a31860fc3fb7c0710cf2d7ed157d3ebab2dafe77` |
| 环境 | Conda `SEProjectV2` |
| Python | 3.11.18 |
| Editable Project | `E:\cityu\SE\project\SE_Project-v2-test` |
| V2 有效需求 | 19 条 |

## 3. 结果摘要

### 3.1 测试

- 全量离线测试：617 passed，0 failed，0 error，16.770s
- V2 专项测试：304 passed
- V1 历史回归：313 passed
- V1 replay：MUST_PASS 11/11，MUST_FAIL 14/14，违规 0
- V2 replay：18 cases，正向 4，预期拒绝 14，违规 0
- Bidding 覆盖率：95.59%，门槛 90%
- 100 候选离线计算：中位数低于 50ms
- 变异验证：25/25

### 3.2 Live

- Live Smoke：PASS
- Live 正常成交：`ad_002`，relevance 95，成交价 200 分
- Live 幂等重放：PASS，输出一致，无重复扣费
- Live 医疗拒绝：PASS，`compliance_rejected`，扣费 0
- Live 错误 key：PASS，`llm_error`，扣费 0
- Live 结构质量：20/20
- Live p50 / p95 / max：1.728s / 2.426s / 2.801s
- Live p95 阈值：5.0s，PASS
- Live 语义质量：PENDING HUMAN LABELS

## 4. Live 成本口径

价格采用 `deepseek-flash` 人民币 token 单价。

### 4.1 高峰价格

- 缓存命中输入：0.04 CNY / 1M tokens
- 缓存未命中输入：2 CNY / 1M tokens
- 输出：8 CNY / 1M tokens

### 4.2 空闲价格

- 缓存命中输入：0.02 CNY / 1M tokens
- 缓存未命中输入：1 CNY / 1M tokens
- 输出：4 CNY / 1M tokens

### 4.3 20 次 p95 批次用量

| 项目 | 数量 |
|---|---:|
| Prompt cache hit | 2,560 tokens |
| Prompt cache miss | 2,720 tokens |
| Completion | 3,142 tokens |
| Total | 8,422 tokens |
| 高峰成本估算 | 0.0306784 CNY |
| 空闲成本估算 | 0.0153392 CNY |

以上 token 和成本只统计 20 次 p95 批次，不是全部 Live 调用的累计值，实际账单以供应商结算为准。

## 5. Live 样本边界

- p95 批次只覆盖一个场景：`morning/mobile/student`
- 报价 sidecar 只有 `ad_001`、`ad_002`
- 20 次真实调用全部选择 `ad_002`
- relevance 范围为 90-95
- 因此该批次证明单场景稳定性、结构合法性和运行性能，不代表全局语义质量

## 6. V2 需求覆盖

19 条 V2 有效需求均已纳入注册表和覆盖映射，分为：

- 报价和评分：`NFR-SAFETY-006/007`、`SEC-002`、`ARCH-009/010/011`
- 竞价与预算：`ARCH-005/006/007/008`、`FR-005/006/007`
- AI 权限边界与审计：`ARCH-012`、`FR-008`
- 质量、评估和性能：`NFR-QA-003/004`、`NFR-PERF-002`
- 治理：`GOV-003`

具体 test evidence 和 runtime monitor 映射由 `docs/code-governance/acceptance-coverage-map.yaml` 和 `docs/architecture/trace-matrix.md` 维护。

## 7. 门禁状态

| Gate | 结果 | 说明 |
|---|---|---|
| Gate 1 Test approval | FAIL | 10 个 V2 测试文件缺少 human pre-approval |
| Gate 2 Static analysis | PASS | Ruff、mypy、依赖、安全路径/fitness |
| Gate 3 Schema | PASS | requirements registry 校验通过 |
| Gate 4 Semantic evaluation | PASS | V1/V2 replay 均通过，违规 0 |
| Gate 5 Regression | PASS | 617 个历史与新增离线测试通过 |
| Gate 6 AI-use log | PASS | 同一变更集已更新 AI-use log |
| Branch protection | NOT VERIFIED | 远程保护和 required checks 未核验 |

## 8. 已知问题和风险

### 8.1 产品功能

本次已执行范围内未发现 V2 产品功能失败。

### 8.2 测试配置问题

- 首次 Live endpoint 使用 API base URL，HTTP 404；修正为完整 `/chat/completions` 后通过。
- 首次医疗 fixture 使用 UTF-8 BOM，JSON 加载器正确 fail-closed；改为无 BOM UTF-8 后通过。

### 8.3 治理与交付阻断

- Gate 1 缺少正式 human pre-approval。
- V2 正式人工验收仍为 `pending_human_acceptance`。
- Live semantic quality 缺少 human-labeled 场景。

## 9. 最终结论

```text
V2 Deterministic Offline Functionality: PASS
V2 Security and Settlement Boundaries: PASS
V2 Live Operational: PASS
V2 Live Performance: PASS
V2 Live Cost: ESTIMATED
V2 Live Semantic Quality: PENDING HUMAN LABELS
V2 Governance: CHANGES REQUIRED
V2 Course Delivery Readiness: CHANGES REQUIRED
```

本报告支持 V2 确定性离线功能、结算安全边界、运行性能和基本真实模型接入的阶段性结论。
