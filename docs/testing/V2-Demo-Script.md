# CS5351 V2 截图演示脚本

## 1. 演示信息

- 版本：V2
- 测试代码 Commit：`e1711d641077ad9be29ad44bde1580d5d8b219d5`
- 证据快照 Commit：`00fc22d0aa6587258e25c8fddbe3996bb36dd81f`
- Run ID：`v2-20261118-e1711d6-01`
- 环境：Conda `SEProjectV2`
- Python：3.11.18
- 演示方式：终端截图 + 原始 evidence
- 测试日期：2026-11-18

## 2. 演示范围

覆盖：

- V2 确定性竞价
- pay-as-bid 成交价
- SQLite 预算、结果与审计原子提交
- 幂等与预算耗尽
- 安全与结算边界
- V1 历史回归
- 固定评估集
- 覆盖率、性能和变异
- 真实 DeepSeek Live smoke
- Live p95、token 与成本

不覆盖：

- Human-labeled Live semantic quality
- 真实支付或曝光
- 远程 CI 和 branch protection 的实际结果

## 3. 截图清单

保存目录：

`evidence/v2/v2-20261118-e1711d6-01/07-demo/screenshots/`

| 编号 | 文件名 | 展示内容 |
|---|---|---|
| 01 | `01-environment.png` | V2 commit、环境、模块路径 |
| 02 | `02-offline-tests.png` | 617 个离线测试 |
| 03 | `03-v2-demo-summary.png` | 七场景竞价演示 |
| 04 | `04-cli-idempotency-budget.png` | 幂等、预算和 exhausted |
| 05 | `05-replay.png` | V1/V2 固定 replay |
| 06 | `06-security-settlement.png` | 安全与结算边界 |
| 07 | `07-quality-checks.png` | 覆盖率、性能和变异 |
| 08 | `08-live-normal.png` | Live 正常成交与幂等 |
| 09 | `09-live-rejections.png` | 医疗拒绝和错误 key |
| 10 | `10-live-performance-cost.png` | p95、token 和成本 |
| 11 | `11-gates-limitations.png` | Gate 结果、阻断和最终结论 |

## 4. 截图规则

- 每张截图必须同时包含标题、关键结果和证据文件名。
- 不显示 API key、Authorization 或完整 endpoint query。
- 所有 Live 结论必须标注固定时间和样本范围。
- 不得把 `PENDING HUMAN LABELS` 写成 PASS。
- 不得把成本估算写成供应商最终账单。

## 5. 最终结论

```text
V2 Offline: PASS
V2 Live Operational: PASS
V2 Live Performance: PASS
V2 Live Cost: ESTIMATED
V2 Live Semantic Quality: PENDING HUMAN LABELS
V2 Governance: CHANGES REQUIRED