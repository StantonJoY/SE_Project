# V3 阶段性测试报告

> 报告状态：FULL_REGRESSION_BLOCKED_BY_TRACKING
> 功能结论：V3 CORE PASS；全量回归待文档提交后重跑；V1/V2 INTEGRATION PENDING
> 课程交付准备度：NOT READY
> 初始 Run ID：`v3-20261120-53d37fc-01`
> 修复后 Run ID：`v3-20261120-15cc289-01`
> 测试日期：2026-11-20
> 原始测试 Commit：`53d37fcf933013af46714a7b29c084e4e07a6696`
> 修复后 Commit：`15cc2895a2ee6c60732a1d8a9a84d384ce009a0d`

## 1. 结论摘要

环境和测试收集阶段通过：

- Conda `SEProjectV3` 可用；
- editable install 指向 V3 worktree；
- app/corpus/compliance/bidding 均来自 V3；
- V1/V2 路径未进入 sys.path；
- 测试收集 675 个，退出码 0。

原数据完整性失败已定位并完成本地修复：

- `items.jsonl` 和 `tags.jsonl` 被团队确认为最终数据；
- manifest 的两个 SHA-256 字段已更新为实际文件 hash；
- corpus 专项测试修复后 22 项通过；
- 修复已提交为 `15cc289`；
- V3 核心 49 项已通过；
- 全量回归被 3 个未跟踪的 V3 测试文档阻断；
- V1/V2 集成、replay、全量测试、变异和 demo 尚未执行。

## 2. 已确认结果

| 项目 | 结果 |
|---|---|
| 测试环境 | PASS |
| 模块隔离 | PASS |
| 工作区 clean | PASS |
| 测试收集 | PASS，675 |
| manifest rows | 5000 |
| bids sidecar 数量 | 5000 |
| bid/budget 检查 | PASS，异常 0 |
| 最小 bid | 1 分 |
| corpus 专项测试 | PASS（本地修复后，22 项） |
| V3 核心专项测试 | PASS，49 项 |
| 全量 pytest | FAIL（未跟踪测试文档） |

## 3. Findings

### F-001 · High · 数据文件和 manifest hash 不一致（manifest 元数据过期）

实际值与 manifest 期望值不一致，corpus 专项测试已失败。当前不能断言 V3 语料可信，也不能继续把后续功能结果作为 V3 验收结论。

`git diff` 为 0，`git ls-files --eol` 显示两份文件均为 `i/lf w/lf`，且 LF 归一化后的 hash 仍不一致。因此可以排除 Windows CRLF，确认是当前 V3 提交内的数据文件与 manifest 产物不一致。

最终 `items.jsonl`/`tags.jsonl` 已由团队确认为权威数据；manifest 只应更新两个 hash，不应修改语料或测试。

状态：`RESOLVED · FIX COMMITTED · CORE VERIFIED`

### F-002 · Closed · handover 与 manifest 的计数口径不同

`HANDOVER-V3.md` 写 `34` 条空 genres、`715` 条 age>=13；manifest 写 `32` 和 `707`。实际复核确认原始总数为 `34/715`；manifest 的 `32/707` 是入选原因分类计数，demo 条目优先归入 `demo`，不是数据缺失。

状态：`CLOSED · EXPLAINED`

### F-003 · Closed · 深度统计命令执行失败

首次 Python 统计因 PowerShell 命令传递报 `NameError`，不是产品测试结果。改用独立 Python 检查脚本后复核成功，数据结构和边界样本均已确认。

状态：`CLOSED · TOOLING`

### F-004 · Medium · 未跟踪测试文档触发 repo completeness

全量 pytest 中 `test_repo_completeness.py::test_checker_passes_on_current_tree` 失败，原因是以下文件尚在磁盘但未被 Git 跟踪：

```text
docs/testing/V3-Test-Execution.md
docs/testing/V3-Test-Report.md
docs/testing/V3_Test_Plan.md
```

这不是 V3 业务代码失败，但会阻断 CI 和全量回归。必须先提交文档，再用新 commit 重跑全量测试。

状态：`OPEN · TRACKING FIX REQUIRED`

## 4. 尚未覆盖

- CorpusRepository fail-closed；
- 5,000 条投影和 `AD_SCHEMA`；
- 确定性 top-K；
- family/campus/competitive 三档矩阵；
- Among Us warnings 并集反例；
- 年龄兜底；
- V1 `--corpus`；
- V2 5% 定价、幂等、预算耗尽；
- V1/V2/V3 replay；
- 全量 pytest；
- mutation 33/33；
- video demo。

## 5. 当前验收判定

```text
V3 Environment: PASS
V3 Test Collection: PASS
V3 Data Integrity: PASS
V3 Core Functional Tests: PASS（49 项）
V3 Full Regression: BLOCKED BY UNTRACKED TEST DOCS
V3 V1/V2 Integration: NOT EVALUATED
V3 Regression: NOT RUN
V3 Governance: NOT READY
V3 Video Demo: NOT READY
```

## 6. 下一步

先提交 CLI 的 V3 测试文档，再用新 commit 重跑全量 pytest。全量回归通过后再执行 V1/V2 端到端、replay、mutation 和 video demo。
