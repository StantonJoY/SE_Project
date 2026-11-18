# Agent 会话记录（D5）

本目录保存 **AI coding agent 的真实会话记录**，用于回答课程的两类问题：
agent 实际承担了什么、什么时候被调用、人类如何审核/纠正/重定向它们。

## 记录清单

| # | 会话 | 日期 | 主题 | 可读版 | 原始记录 |
|---|---|---|---|---|---|
| 1 | `session-a8810df4` | 2026-10-06 → 11-02 | **V1 从零构建**：需求 → 架构 → 治理工件 → 7 个架构元素 → 评估集；39 轮 / 1149 次工具调用 / 16 次审批 | [`2026-10-06-v1-build-and-governance.md`](2026-10-06-v1-build-and-governance.md)（精简模式） | `raw/2026-10-06-session.v4.jsonl.zstd` |
| 2 | `session-7cc4a18d` | 2026-11-17 | V1→V2 整合、CI 失效根因定位与修复、PR 合并、D5 补齐 | [`2026-11-17-main-v2-integration.md`](2026-11-17-main-v2-integration.md) | `raw/2026-11-17-session.v4.jsonl.zstd` |
| 3 | `session-b0e6882` | 2026-11-04 → 11-11 | **V1 测试与证据**：Mock/Offline 测试、证据采集、截图演示、推送验证；45 轮 / 175 次工具调用 / 0 次审批，源事件 425 条 | [`2026-11-04-v1-testing-and-evidence.md`](2026-11-04-v1-testing-and-evidence.md) | `raw/2026-11-04-session.v4.jsonl.zstd` |
| 4 | `session-5486afbc` | 2026-11-16 → 11-18 | **V2 测试与验证**：独立 worktree/Conda、竞价与结算、V1 回归、Live 测试、截图演示、证据封装；摘要 18 轮 / 20 个工具块，原始 84 轮 / 120 次工具调用 / 0 次审批 | [`2026-11-18-v2-testing-and-evidence.md`](2026-11-18-v2-testing-and-evidence.md) | `raw/2026-11-16-session.v4.jsonl.zstd` |

> 长会话（工具调用上千次）用 `--compact` 导出：助手正文截到 600 字符、工具调用按名称聚合，
> 单条细节回 `raw/` 里查。短会话用完整模式，保留逐条工具参数与结果。

> 后续会话请按同一格式补充：可读版放本目录，原始 `session.v4.jsonl.zstd` 放 `raw/`，并在此表登记。

## 这批记录能说明什么

以第 1 份为例，它完整保留了这些可核查的事实（不是事后叙述）：

- **人类下指令 → agent 执行 → 人类打断/改向**：中途有人类消息直接改变任务（"我们先简单做一下，只跑 python 测试"、"tests.yml 不要了"、"起 PR"）；
- **agent 遇到阻塞并上报**：沙箱权限导致 `pwsh` 全挂、测试套件"卡住"、CI 7 次运行 0 job；
- **人类批准了哪些提权**：3 次 `approval/asked` + `approval/decided`，含被允许的范围；
- **工具调用全过程**：189 次调用与结果（含失败），可直接核对 agent 到底做了什么；
- **没有做的事**：例如 agent 从未修改 `src/compliance/`、`data/*.json`。

## 生成方式

可读版由本仓库脚本生成，可复现、非手写：

```bash
node transcripts/tools/export-session.js \
     transcripts/raw/2026-11-17-session.v4.jsonl.zstd \
     transcripts/2026-11-17-main-v2-integration.md
```

脚本只做排版（截断长文本、跳过模型内部 `reasoning` 块、标注平台注入内容），
**不改写用户消息与助手正文**。原始字节在 `raw/` 中完整保留，可独立校验。
