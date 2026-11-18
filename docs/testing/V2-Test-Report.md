# V2 阶段性测试报告

## 1. 测试范围

本次覆盖 V2 确定性竞价、预算结算、幂等、事务、安全边界、审计、固定评估、V1 回归及离线端到端演示。
Live smoke、拒绝路径、幂等、20 次 p95 以及 token/成本估算

不包含：

- human-labeled live semantic quality
- 真实支付或曝光

## 2. 基线

- 分支：`test/v2-validation`
- Commit：`e1711d641077ad9be29ad44bde1580d5d8b219d5`
- 来源：`origin/feat/v2-agent-workflow`
- 环境：`SEProjectV2`
- Python：3.11

## 3. 结果摘要

- V1 + V2 全量离线测试：617 passed
- V2 专项测试：304 passed
- V1 历史回归：313 passed
- V1 replay：11/11 + 14/14
- V2 replay：18 cases，违规 0
- Bidding 覆盖率：>90%
- 100 候选计算：<50ms
- 变异验证：25/25
- Gate 4：PASS
- Gate 6：PASS
- Gate 1：FAIL
- Live Smoke：PASS
- Live p95：PASS，2.426 秒，阈值 5 秒
- Live Token：8,422
- Live 成本：高峰估算 0.0306784 CNY；空闲估算 0.0153392 CNY
- Live 结构质量：20/20
- Live 语义质量：PENDING HUMAN LABELS

## 4. 结论

```text
V2 Deterministic Offline Functionality: PASS
V2 Security and Settlement Boundaries: PASS
V2 Test Approval / Governance: CHANGES REQUIRED
V2 Live Smoke: PASS WITH LIMITATIONS
V2 Live Cost: ESTIMATED
V2 Live Operational: PASS
V2 Live Performance: PASS
V2 Live Semantic Quality: PENDING HUMAN LABELS
V2 Course Delivery Readiness: CHANGES REQUIRED