# V2 测试执行记录

> 状态：COMPLETED_WITH_LIMITATIONS
> Run ID：`v2-20261118-e1711d6-01`
> 分支：`test/v2-validation`
> Commit：`e1711d641077ad9be29ad44bde1580d5d8b219d5`
> 环境：`SEProjectV2`
> 模式：Offline PASS；Live operational PASS；Live semantic quality PENDING HUMAN LABELS

## 执行结果

| ID | 检查项 | 结果 | 证据 |
|---|---|---|---|
| V2-ENV-001 | 环境与源码绑定 | PASS | `pip-show-ad-recommender.txt` |
| V2-COL-001 | 测试收集 | PASS，617 | `pytest-collect.stdout.txt` |
| V2-STA-001 | Ruff | PASS | `ruff.stdout.txt` |
| V2-TYPE-001 | mypy | PASS，40 文件 | `mypy.stdout.txt` |
| V2-DEP-001 | 依赖 | PASS | `dependencies.stdout.txt` |
| V2-SCHEMA-001 | 需求 Schema | PASS | `schema.stdout.txt` |
| V2-FIT-001 | Fitness | PASS | `fitness.stdout.txt` |
| V2-REPO-001 | 仓库完整性 | PASS | `repo-completeness.stdout.txt` |
| V2-IMPL-001 | 实现一致性 | PASS，0 发现 / 78 通过 | `implementation-audit.stdout.txt` |
| V2-SAFETY-001 | 安全路径与 ADR | PASS | `safety-paths.stdout.txt` |
| V2-GATE1-001 | Gate 1 | FAIL，10 个测试缺少前置批准 | `test-approval.stdout.txt` |
| V2-GATE4-001 | Gate 4 | PASS | `semantic-eval.stdout.txt` |
| V2-GATE6-001 | Gate 6 | PASS | `ai-use-log.stdout.txt` |
| V2-V2REG-001 | V2 专项测试 | PASS，304 | `v2-targeted.junit.xml` |
| V2-V1REG-001 | V1 回归 | PASS，313 | `v1-regression.junit.xml` |
| V2-FULL-001 | 全量离线测试 | PASS，617 | `offline-full.junit.xml` |
| V2-REPLAY-001 | V1 replay | PASS，11/11 + 14/14 | `v1-replay.stdout.txt` |
| V2-REPLAY-002 | V2 replay | PASS，18 cases，违规 0 | `v2-replay.json` |
| V2-COV-001 | Bidding 覆盖率 | PASS，>90% | `bidding-coverage.xml` |
| V2-PERF-001 | 性能 | PASS，<50ms | `performance.stdout.txt` |
| V2-MUT-001 | 变异验证 | PASS，25/25 | `mutation.stdout.txt` |
| V2-E2E-001 | 七场景演示 | PASS | `v2-demo-clean.stdout.json` |
| V2-E2E-002 | CLI 成交与幂等 | PASS，spend=440，audit=3 | `cli-final-db.txt` |
| V2-LIVE-SMOKE-001 | Live 正常成交 | PASS，ad_002，relevance=95，price=200，耗时 3.059s | `live-smoke-2.stdout.json` |
| V2-LIVE-002 | Live 相同 request_id 重放 | PASS，输出 Hash 一致，无重复扣费 | `live-replay-2.stdout.json` |
| V2-LIVE-003 | Live 医疗品类拒绝 | PASS，no_ad/compliance_rejected，扣费 0 | `live-medical-2.stdout.json` |
| V2-LIVE-004 | Live 错误 API key | PASS，no_ad/llm_error，扣费 0 | `live-bad-key.stdout.json` |
| V2-LIVE-P95-001 | Live p50/p95/max | PASS，p50=1.728s，p95=2.426s，max=2.801s | `live-p95-results.json` |
| V2-LIVE-COST-001 | Live token 与成本 | PASS，8422 tokens；高峰 0.0306784 CNY；空闲 0.0153392 CNY | `live-p95-results.json` |
| V2-LIVE-QUALITY-001 | Live 语义质量 | PENDING HUMAN LABELS | `live-p95-results.json` |

### Live 配置诊断

- Live 测试已经证明 API smoke、拒绝路径、幂等、p95 和 token 成本。
- 完整 live semantic quality 仍需要 human-labeled 场景。

## 关键结果

- 相同 request_id 重放输出一致，无重复扣费。
- `ad_001` 花费 240 分后 exhausted。
- 下一请求切换至 `ad_002`，扣费 200 分。
- 最终总花费 440 分，审计 3 条，唯一请求 3 条。
- V1 与 V2 replay 违规均为 0。

## 当前阻断

- Live semantic quality 仍为 PENDING HUMAN LABELS。
- 完整可重复 live quality suite 未建立。