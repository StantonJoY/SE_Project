# V2 交付总结与证据索引

> 核对日期：2026-11-22。基于 `main` 提交 `6578062`；本次为文档收尾，未修改产品代码或测试断言。课程要求以最初的 CS5351 项目说明 PDF 为准。

## 1. 已交付的范围

V2 在 V1 上增加确定性单赢家竞价和持久预算管理。模型只提供候选相关性，代码按 `relevance × bid_cents` 排序，以 `ad_id` 升序解平局，使用 pay-as-bid。合规层保留最终否决权；被拒绝的广告不收费，也不自动递补次优候选。金额均为整数分，是本地账本模拟，未接真实支付或曝光确认。

核心实现随 [PR #2](https://github.com/StantonJoY/SE_Project/pull/2) 合入 main，合并提交 `143cba6`；成员 C 的个人自评随 [PR #5](https://github.com/StantonJoY/SE_Project/pull/5) 合入，合并提交 `7c459c9`。后续 V3 接入真实语料并复用 V2，语料采集、内容分级与定价映射属于 V3，不能全部归为个人 V2 成果。

## 2. 需求、组件与验证

V2 的 19 条需求 ID 均在原注册表中。下表中的简写均带 `REQ-ADS-` 前缀；完整 fit criterion 和逐条测试映射以 [需求注册表](../req/requirements.yaml)、[覆盖表](../code-governance/acceptance-coverage-map.yaml)及 [追踪矩阵](../architecture/trace-matrix.md)为准。

| 需求 ID | 实现与职责 | 验证入口 |
|---|---|---|
| NFR-SAFETY-006、ARCH-008、SEC-002 | `bidding.models.validate_bids`：严格整数、范围、重复/未知 ID 与报价校验 | `test_bidding_v2.py` |
| ARCH-009、ARCH-010、ARCH-011、FR-005 | `bidding.engine.choose_winner`、`Ledger.finalize`：确定性排名、平局和成交价 | `test_bidding_v2.py`、`test_v2_settlement_boundaries.py` |
| ARCH-005、ARCH-006、ARCH-007、FR-007、FR-008 | `bidding.ledger`、`pipeline_v2`：预算不变量、候选资格、精确扣费、耗尽和审计快照 | `test_bidding_v2.py`、`test_pipeline_v2.py`、`test_v2_settlement_boundaries.py` |
| NFR-SAFETY-007、ARCH-012 | `selector.relevance`、`pipeline_v2`：评分严格解析、闭集建议、经济字段由代码产生 | `test_relevance_v2.py`、`test_v2_boundary_regressions.py` |
| FR-006、GOV-003 | 严格配置和治理脚本：唯一公式、语义变更回放、ADR、测试批准及 AI 使用日志检查 | `test_v2_governance.py` |
| NFR-QA-003、NFR-QA-004、NFR-PERF-002 | 离线竞价、18 条固定评估和演示、计算开销测试 | `test_v2_eval.py`、`test_v2_governance.py`、`test_bidding_v2.py` |

测试路径均位于 `test/offline/`。12 条 V2 不变量及其反例另见覆盖表。存在测试映射不等于全部需求已取得正式人工验收。

## 3. 数据流与持久状态

完整英文说明已补入 [Report §2.3](../../Report.md#23-v2-auction-between-advice-and-authority)。代码入口为 [pipeline_v2.py](../../src/app/pipeline_v2.py) 和 [ledger.py](../../src/bidding/ledger.py)。

```text
request_id + 场景/报价/版本指纹
  → 查询已保存请求：同输入返回原结果；冲突拒绝
  → 场景/报价/余额筛选 → 注入检查与上下文预算
  → 模型相关性 JSON → 严格闭集解析
  → 确定性竞价 → 最终合规 → 输出 Schema
  → SQLite 同事务重查余额、扣费、保存结果与审计
```

同 ID 重放不新增模型调用、扣费或审计。事务阶段故障回滚；若存储结果无法可靠确认，则返回 `status_unknown` 并要求使用相同 ID 和相同输入恢复。不能据此声称“肯定未扣费”。审计不可用时也不能保证持久证据已经写入。

V2 权威审计在 SQLite 的 `audit.record_json` 中，保留场景、候选、报价/预算、模型输出、评分、合规步骤及版本来源。当前尚未实现统一 `monitors` 采集；审计中的 `user_tags` 最小化和保留期/防篡改决策仍有技术债（TD-007/008）。

## 4. 本次验证与已有证据

本次运行基于上述源提交，使用 Windows / Python 3.12.14、固定离线模型；HTTP 边界测试仅使用本机回环。原始输出和命令见 [本次验证目录](../../evidence/v2/v2-20261122-6578062-docs-check/README.md)，不是历史构建记录。

| 检查 | 本次结果 | 范围 |
|---|---|---|
| 需求 Schema 与架构 fitness | 通过 | 当前注册表与结构检查 |
| 8 个 V2 离线测试模块 | 303 通过、1 因回环受限跳过；该项放开本地端口后单独重跑通过 | 不是全项目回归结论 |
| 竞价模块语句覆盖率 | 95.59%，达到 90% 门槛 | `src/bidding` |
| `scripts/demo_v2.py` | 7 项演示通过 | 竞价、重放、耗尽、换候选、重启、拒绝零扣费、故障回滚 |
| `eval/v2_runner.py` | 18 条：4 正向、14 预期拒绝，违规 0 | 固定离线 replay，不代表真实模型质量 |

既有证据：

- [历史 V2 固定回放](../../evidence/v3/v3-20261120-4d0479f-01/09-replay/v2-replay.stdout.txt)：18 条、违规 0。
- [V2 corpus E2E](../../evidence/v3/v3-20261120-4d0479f-01/08-v2-e2e/)：首次预算 6000→5700，同 ID 重放不扣费，新 ID 再扣 300 后为 5400，冲突拒绝。该批使用固定离线评分。
- [历史本地交付预演与 CityU smoke](../review-memo.md)：2026-11-05 全量 617 测试通过，随后真实模型 `CS5351/DeepSeek-V4-Flash` 的成交、重放和医疗品类拒绝验证；这些是各自日期的结果。
- [后续 relevance live harness](../../test/live/run_v2_relevance_live.py)及 [V3 live 报告](V3-Live-Prompt-Semantic-Report.md)：`deepseek-flash` 直接客户端实验，6 场景 × 5 次结构 30/30，两组对照各 5/5；范围有限，不能单独证明完整 live 管道的审计 provenance 持久化，也不能与前一批 smoke 合并成同一次实测。

## 5. 过程与协作状态

| 项目 | 核对结论 |
|---|---|
| 实施计划和架构选择 | 原计划保留；SQLite 原子结算、被否候选及理由见 [ADR-005](../architecture/adr-005-v2-atomic-auction.md) |
| Agent 分工及干预 | 实际为 Codex agents；PLAN/TEST/BUILD/VERIFY 和技术重定向摘要见 [V2 执行计划](../plans/V2-execution.md)、[AI 使用日志](../ai-use-log.yaml)、[评审备忘](../review-memo.md) |
| 人工批准 | `TA-0006` 已记录部分既有测试的事后验收；历史实现前批准证据仍缺失，全 V2 正式验收仍 pending，见 [审批状态](../v2-approval-status.yaml) |
| D5 会话材料 | 仓库已有 V2 可读文件及导出文件；原始完整性与人工干预标注仍需按课程要求核对。整理稿、导出稿不能仅凭存在就视为完整原始会话 |
| 远端 CI | 已实际执行；本次核对的 main [运行 45029164091](https://github.com/StantonJoY/SE_Project/actions/runs/45029164091)失败，Gate 5 回归问题未解决，不能用本地 V2 定向测试替代全项目 CI |
| 分支保护 | main 存在 6 项必需检查、Code Owner review 和禁止非快进规则；管理员 bypass 的边界见 [分支保护说明](../branch-protection.md) |

## 6. 仍待完成的边界

- TD-001 的 V2 runtime monitor 接线及聚合器需要实际实现和测试，仍开放；[监控方案](../plans/TD-001-monitor-wiring.md)不是实现证据。
- 历史前置批准缺口不能回填；后续测试变更须依据当时有效流程先取得真实批准。
- 当前远端全项目回归故障、广泛人工标注质量、真实线上 p95、实际费用和完整 live 管道审计验证尚未完成。
- D5 原始会话完整性、姓名/学号、贡献比例和最终报告排版/命名需使用真实团队资料；本轮不替团队生成这些事实。

本轮完成的是 V2 交付说明、报告数据流、状态校核及可重跑的验证索引；未把这些剩余项标记为完成。
