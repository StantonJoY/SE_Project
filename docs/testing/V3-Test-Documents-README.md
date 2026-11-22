# V3 测试文档索引

> 测试代码 Commit：`161381887e421a121cd2878fcbf397d42a8ac818`
> 当前 Run ID：`v3-20261120-1613818-01`
> 测试环境：Conda `SEProjectV3` / Python 3.11.18
> 文档状态：TEST_EXECUTION_COMPLETE / SCREENSHOT_DEMO_COMPLETE / EVIDENCE_COMPLETE / GATE1_DEFERRED

## 文档清单

| 文件 | 作用 | 当前状态 |
|---|---|---|
| `V3-Test-Execution.md` | 命令、结果、失败修复过程、证据目录 | 已完成 |
| `V3-Test-Report.md` | 阶段结论、Findings、验收判定 | 已完成 |
| `V3-Live-Prompt-Semantic-Report.md` | 真实 HTTP relevance 语义评估 | PASS_WITH_LIMITATIONS |
| `V3-live-prompt-human-labels.json` | 人工确认的场景标签和限制 | CONFIRMED |
| `V3-V1-Live-Prompt-Semantic-Report.md` | V1 `ctx-v1.1` test-only live probe | PASS_WITH_LIMITATIONS |
| `V3-v1-live-prompt-human-labels.json` | V1 test-only live 的限制说明 | CONFIRMED |
| `V3-Demo-Script.md` | Screenshot demo 的 10 张截图、命令和限制 | COMPLETE（10/10） |
| `V3-Demo-Screenshots.md` | 10 张最终截图索引和图片链接 | COMPLETE（10/10） |

## 已验证结果

```text
V3 core tests: 49 PASS
Full offline regression: 675 PASS
V1/V2 E2E: PASS
V1/V2/V3 replay: PASS
Mutation: 33/33 PASS
Ruff/mypy/deps/schema/fitness/repo/safety/audit: PASS
Coverage: 86% total
Live prompt structural validity: 30/30
Title-bait: 5/5
Known-title: 5/5
Live prompt semantic quality: PASS_WITH_LIMITATIONS
```

## Live 测试工具

仓库中的 `test/live/` 保存真实模型测试入口，不进入离线 CI 默认路径：

| 文件 | 用途 |
|---|---|
| `run_v1_live_semantic.py` | 通过 `app.pipeline.recommend` 注入真实 HTTP client，测试 V1 `ctx-v1.1` |
| `run_v2_relevance_live.py` | 通过产品支持的 HTTP relevance 路径测试 V2 `relevance-v2.2` |
| `filter_v1_live_audit.py` | 从追加式 audit 文件中提取最终 18 条 V1 live 记录 |
| `README.md` | 环境变量、运行方式、输出位置和边界 |

这些工具只从环境变量读取凭据，不保存 API key。

## 尚未完成

- Gate 1 Test approval：`DEFERRED / FAIL`；
- family/gamer 独立 CLI 审计 detail 取证；
- 最终文档、live 工具和 evidence 的 Git commit。

## 重要限制

- V1 产品 CLI 仍为 Mock/Offline；测试 harness 已补 `ctx-v1.1` live probe，当前为已人工确认的 `PASS_WITH_LIMITATIONS`。
- V2 live semantic 覆盖 `relevance-v2.2`，6 个场景各 5 次。
- V1 live 是 test-only harness，覆盖 `ctx-v1.1`，6 个场景各 3 次；V1 产品 CLI 未切换为 live。
- 真实模型只测试 `deepseek-flash`。
- 标题诱导和名作对照是合成样本，不是完整人类 gold corpus。
- Live 结果不能替代固定 replay、全量回归或合规测试。
- Gate 1 仍是课程正式交付阻断项。

## 最终口径

```text
V3 Functional Testing: PASS
V3 Regression / Replay / Mutation / Static / Coverage: PASS
V3 Live Prompt: PASS_WITH_LIMITATIONS
V3 Governance: DEFERRED / FAIL
V3 Screenshot Demo: COMPLETE（10/10）
V3 Evidence Package: COMPLETE
V3 Course Delivery Readiness: CHANGES REQUIRED
```
