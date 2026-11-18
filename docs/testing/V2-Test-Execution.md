# V2 测试执行记录

> 状态：COMPLETED_WITH_LIMITATIONS
> Run ID：`v2-20261118-e1711d6-01`
> 测试日期：2026-11-18
> 分支：`test/v2-validation`
> 测试代码 Commit：`e1711d641077ad9be29ad44bde1580d5d8b219d5`
> 证据快照 Commit：`00fc22d0aa6587258e25c8fddbe3996bb36dd81f`
> 基线 Commit：`a31860fc3fb7c0710cf2d7ed157d3ebab2dafe77`
> 环境：Conda `SEProjectV2`
> Python：3.11.18
> Editable Project：`E:\cityu\SE\project\SE_Project-v2-test`
> 模式：Offline PASS；Live operational PASS；Live semantic quality PENDING HUMAN LABELS

## 1. 测试范围

本次执行覆盖：

- V2 竞价、预算、结算、幂等、事务与审计
- V1 历史测试回归
- V1 与 V2 固定评估集 replay
- V2 专项离线测试与结构检查
- 覆盖率、性能和变异验证
- V2 CLI 与七场景离线演示
- 真实 HTTP provider 的 smoke、拒绝路径、p95、token 和成本

本次不覆盖：

- human-labeled live semantic quality
- 完整可重复 live quality suite
- 真实支付或曝光确认
- 远程 CI 与分支保护的实际运行结果

## 2. 基线和变更范围

| 项目 | 值 |
|---|---|
| 测试分支 | `test/v2-validation` |
| 来源分支 | `origin/feat/v2-agent-workflow` |
| 测试代码 Commit | `e1711d641077ad9be29ad44bde1580d5d8b219d5` |
| 证据快照 Commit | `00fc22d0aa6587258e25c8fddbe3996bb36dd81f` |
| 基线 Commit | `a31860fc3fb7c0710cf2d7ed157d3ebab2dafe77` |
| V2 有效需求 | 19 条 |
| 相对 main 的变更 | 65 个文件，+6613 / -436 |
| 证据目录 | `evidence/v2/v2-20261118-e1711d6-01/` |

V2 分支修改了 V1 架构、需求、评估和检查器文件，没有建立 `docs2/`。这与仓库此前声明的 V2 append-only 约定存在冲突，需要团队或教师确认，测试本身不擅自判定该组织方式对错。

## 3. 执行结果

| ID | 检查项 | 结果 | 证据 |
|---|---|---|---|
| V2-ENV-001 | Conda 环境与源码绑定 | PASS | `pip-show-ad-recommender.txt`、`module-paths.txt` |
| V2-COL-001 | 测试收集 | PASS，617 | `pytest-collect.stdout.txt` |
| V2-STA-001 | Ruff | PASS | `ruff.stdout.txt` |
| V2-TYPE-001 | mypy | PASS，40 files | `mypy.stdout.txt` |
| V2-DEP-001 | 依赖声明检查 | PASS | `dependencies.stdout.txt` |
| V2-SCHEMA-001 | 需求 Schema 与架构输入校验 | PASS | `schema.stdout.txt` |
| V2-FIT-001 | 架构 fitness function | PASS | `fitness.stdout.txt` |
| V2-REPO-001 | 仓库完整性 | PASS | `repo-completeness.stdout.txt` |
| V2-IMPL-001 | 实现与需求一致性审计 | PASS，0 发现 / 78 通过 | `implementation-audit.stdout.txt` |
| V2-SAFETY-001 | 安全路径与 ADR 伴随检查 | PASS，含 ADR-005 | `safety-paths.stdout.txt` |
| V2-GATE1-001 | Gate 1 测试批准 | FAIL，10 个测试文件缺少 human pre-approval | `test-approval.stdout.txt` |
| V2-GATE4-001 | Gate 4 语义评估 | PASS | `semantic-eval.stdout.txt` |
| V2-GATE6-001 | Gate 6 AI-use log | PASS | `ai-use-log.stdout.txt` |
| V2-V2REG-001 | V2 专项测试 | PASS，304 | `v2-targeted.junit.xml` |
| V2-V1REG-001 | V1 历史回归 | PASS，313 | `v1-regression.junit.xml` |
| V2-FULL-001 | 全量离线测试 | PASS，617，耗时 16.770s | `offline-full.junit.xml` |
| V2-REPLAY-001 | V1 replay | PASS，11/11 + 14/14，违规 0 | `v1-replay.stdout.txt` |
| V2-REPLAY-002 | V2 replay | PASS，18 cases，违规 0 | `v2-replay.json` |
| V2-COV-001 | Bidding 覆盖率 | PASS，95.59% | `bidding-coverage.xml` |
| V2-PERF-001 | 100 候选性能 | PASS，中位数 < 50ms | `performance.stdout.txt` |
| V2-MUT-001 | 变异验证 | PASS，25/25 | `mutation.stdout.txt` |
| V2-E2E-001 | 七场景离线演示 | PASS | `v2-demo-clean.stdout.json` |
| V2-E2E-002 | CLI 成交、幂等与耗尽 | PASS，3 requests，spend=440，audit=3 | `cli-final-db.txt` |
| V2-LIVE-SMOKE-001 | Live 正常成交 | PASS，ad_002，relevance=95，price=200，3.059s | `live-smoke-2.stdout.json` |
| V2-LIVE-IDEMP-001 | Live 相同 request_id 重放 | PASS，输出 Hash 一致，无重复扣费 | `live-replay-2.stdout.json` |
| V2-LIVE-MEDICAL-001 | Live 医疗品类拒绝 | PASS，no_ad/compliance_rejected，扣费 0 | `live-medical-2.stdout.json` |
| V2-LIVE-FAILCLOSED-001 | Live 错误 API key | PASS，no_ad/llm_error，扣费 0 | `live-bad-key.stdout.json` |
| V2-LIVE-P95-001 | Live p50/p95/max | PASS，1.728s / 2.426s / 2.801s | `live-p95-results.json` |
| V2-LIVE-COST-001 | Live token 与成本估算 | PASS，8422 tokens；高峰 0.0306784 CNY；空闲 0.0153392 CNY | `live-p95-results.json` |
| V2-LIVE-SEMANTIC-001 | Live 语义质量 | PENDING HUMAN LABELS | `live-p95-results.json` |

## 4. 关键功能结果

- 相同 request_id、相同输入重放时输出完全一致。
- 重放没有二次模型调用、二次扣费或额外审计。
- `ad_001` 两次成交后 `spent=240`、`remaining=0`、状态 `exhausted`。
- 下一次请求切换至 `ad_002`，扣费 200 分。
- CLI 最终总花费 440 分，审计 3 条，唯一请求 3 条。
- 医疗品类在扣费前被确定性合规层拒绝，`spent=0`。
- 事务故障与并发预算测试全部通过，未发现超支、重复扣费或账实不一致。
- V1 与 V2 replay 均无违规。

## 5. Live 结果

### 5.1 正常成交与拒绝

- 正常成交：`ad_002`，relevance 95，bid/price 200 分，端到端 3.059 秒。
- 相同 request_id 重放：输出 Hash 一致，账本不变。
- 医疗品类：`no_ad/compliance_rejected`，扣费 0。
- 错误 API key：`no_ad/llm_error`，扣费 0。

### 5.2 20 次 p95 与成本批次

| 指标 | 结果 |
|---|---|
| 样本数 | 20 |
| 功能成功 | 20/20 |
| 结构成功 | 20/20 |
| Schema 失败 | 0 |
| Usage 成功 | 20/20 |
| p50 | 1.728s |
| p95 | 2.426s |
| max | 2.801s |
| 阈值 | 5.0s |
| 缓存命中输入 | 2,560 tokens |
| 缓存未命中输入 | 2,720 tokens |
| 输出 | 3,142 tokens |
| 合计 | 8,422 tokens |
| 高峰成本估算 | 0.0306784 CNY |
| 空闲成本估算 | 0.0153392 CNY |

以上 token 和成本仅统计 20 次 p95 批次，不包含正常 smoke、幂等重放、医疗拒绝和错误 key 测试。

### 5.3 样本边界

- 20 次 p95 测试只使用一个场景 `morning/mobile/student`。
- 报价 sidecar 只有 `ad_001` 和 `ad_002` 两个候选。
- 20 次全部选择 `ad_002`，relevance 为 90-95。
- 该结果证明单场景稳定性与运行性能，不代表完整语义推荐质量。

## 6. 测试配置问题

以下问题属于测试配置，不是 V2 产品缺陷：

| 问题 | 结果与处置 |
|---|---|
| 首次 Live endpoint 填成 API base URL | HTTP 404；V2 返回 `no_ad/llm_error`，扣费 0；改为完整 `/chat/completions` 后通过 |
| 首次医疗 fixture 使用 UTF-8 BOM | JSON 加载严格拒绝；改用无 BOM UTF-8 后通过 |

## 7. 当前阻断和风险

- Gate 1 FAIL：10 个 V2 测试文件缺少实现前 human approval。
- `docs/v2-approval-status.yaml` 为 `pending_human_acceptance`。
- Live semantic quality 仍为 `PENDING HUMAN LABELS`。
- 完整可重复 live quality suite 未建立。
- V2 未建立 `docs2/` 并修改 V1 工件，需团队或教师确认。
- 远程 CI 和 branch protection 未核验。
- D5 transcripts、D6 Report.md 仍缺失。

## 8. 执行结论

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

在本次已执行范围内未发现 V2 产品功能失败。
