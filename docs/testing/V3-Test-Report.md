# V3 阶段性测试报告

> 报告状态：LIVE_SEMANTIC_PASS_WITH_LIMITATIONS / GATE1_DEFERRED
> 功能结论：V3 CORE PASS；全量回归 675 PASS；V1/V2 E2E PASS；replay PASS；mutation PASS；static PASS；live prompt PASS_WITH_LIMITATIONS
> 课程交付准备度：NOT READY
> 初始 Run ID：`v3-20261120-53d37fc-01`
> 修复后 Run ID：`v3-20261120-15cc289-01`
> 当前 Run ID：`v3-20261120-1613818-01`
> 测试日期：2026-11-20
> 原始测试 Commit：`53d37fcf933013af46714a7b29c084e4e07a6696`
> 修复后 Commit：`15cc2895a2ee6c60732a1d8a9a84d384ce009a0d`
> 当前 Commit：`161381887e421a121cd2878fcbf397d42a8ac818`
> Handover 对照：核心路径已覆盖；family/gamer 独立审计 detail 尚未单独录制；V2 live semantic 已覆盖；V1 product CLI 为 offline-only，test-only live 为 PASS_WITH_LIMITATIONS

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
- 文档提交为 `4d0479f`；
- 全量回归 675 项通过；
- V1 corpus 正常路径和非法场景均已通过；
- V1 内部 `load/select/project` 为 `0.235s / 0.264s / 0.240s`，满足 500ms 口径；
- 默认 stdout 文件实际为 GBK/CP936，UTF-8 解码失败；
- 设置 `PYTHONIOENCODING=utf-8` 后重跑，V1 JSON 可解析且功能 PASS；
- V2 正常竞价、幂等重放、新请求扣费、场景冲突和预算一致性均通过；
- V1/V2/V3 三套 replay 均通过；
- mutation 33/33 通过；
- mypy、依赖、Schema、fitness、repo completeness、safety paths、implementation audit 通过；
- ruff 首轮 13 项问题已通过自动修复和两项人工修复解决，当前 `ruff check` 返回 0；
- Ruff 修复 commit 为 `1613818`；该 commit 上全量回归 675 PASS、mutation 33/33 PASS；
- AI-use log 和 semantic eval PASS；
- test approval FAIL，发现 7 项 mapping/concrete evidence 缺口；
- 按用户决定暂缓 Gate 1 修复，状态保留为 `DEFERRED / FAIL`；
- 最终静态检查 ruff/mypy/依赖/Schema/fitness/repo/safety/audit 全部 PASS；
- V3 新模块覆盖率总 86%，XML 已生成；项目未声明强制覆盖率门槛；
- video demo 尚未准备。

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
| L3 CorpusRepository / Ad 投影 | PASS，包含在 core 49 |
| L4 确定性与 top-K | PASS，包含在 core 49 |
| L5 内容分级与年龄兜底 | PASS，包含在 core 49 |
| 全量 pytest | PASS，675 项，0 failures / 0 errors |
| V1 正常 corpus E2E | PASS，`ad_16120`，audit=1 |
| V1 非法场景 E2E | PASS，`no_ad/scene_invalid`，audit=1 |
| V1 internal load/select/project | PASS，约 0.24s |
| V1 stdout encoding | FAIL（默认）；PASS（UTF-8 环境） |
| V2 corpus E2E | PASS，`ad_2993780`，charge=300 |
| V2 幂等重放 | PASS，输出 hash 一致 |
| V2 冲突与预算 | PASS，`request_conflict`，无额外扣费，账实一致 |
| V1 replay | PASS，11/11 + 14/14，violations=0 |
| V2 replay | PASS，18 cases，violations=0 |
| V3 replay | PASS，14/14，violations=0，p95=3.4ms |
| Mutation | PASS，33/33 |
| Ruff | FAIL，13 项 |
| mypy / deps / schema / fitness | PASS |
| static safety/repo/audit | PASS |
| AI-use log | PASS |
| Semantic eval | PASS |
| Test approval | FAIL，7 项映射/证据缺口 |
| Final static gate | PASS，8/8 项 |
| V3 new module coverage | 86% total（无强制门槛） |
| Live prompt structural validity | PASS，30/30 |
| Live prompt semantic quality | PASS_WITH_LIMITATIONS；6 scenes，30/30 + 10/10；人工确认 |

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

### F-004 · Closed · 未跟踪测试文档触发 repo completeness

全量 pytest 中 `test_repo_completeness.py::test_checker_passes_on_current_tree` 失败，原因是以下文件尚在磁盘但未被 Git 跟踪：

```text
docs/testing/V3-Test-Execution.md
docs/testing/V3-Test-Report.md
docs/testing/V3_Test_Plan.md
```

这不是 V3 业务代码失败，但会阻断 CI 和全量回归。提交三份文档后，使用新 commit 重跑全量测试已通过。

状态：`CLOSED · DOCS COMMITTED · FULL REGRESSION PASS`

### F-005 · Low · V1 CLI 耗时观测需拆分

当前正常 CLI 运行耗时 `1.029s`，高于 handover 的 `<1s` 参考值，也高于需求中 500ms 的内部处理口径。后续已拆分测量：内部 load/select/project 为 `0.235s / 0.264s / 0.240s`，内部性能通过；CLI 端到端仍记录为包含进程启动的观测值。

状态：`CLOSED · INTERNAL PERFORMANCE PASS`

### F-006 · High · stdout JSON 不是 UTF-8

V1 正常 stdout 文件以 UTF-8 解码在 byte `0xd4` 失败；同一文件用 GBK/CP936 可以解码。该问题影响机器可读输出和跨平台重放，不是终端显示问题。

状态：`MITIGATED · UTF-8 ENV PREREQUISITE`；产品默认输出契约仍待团队决定

### F-007 · Closed · Ruff 静态门禁

`ruff check src test scripts eval` 首轮 13 项，已自动修复 11 项；剩余 `zip(..., strict=False)` 和 `isinstance(..., (property, dict))` 两项也已完成。修复提交为 `1613818`，`ruff check` 当前返回 0。

状态：`CLOSED · POST-FIX REGRESSION PASS`

### F-008 · High · Gate 1 test approval 未通过

`check_test_approval.py --base origin/main` 返回 1，记录 7 个问题：

```text
eval/v3_runner.py: no requirement-to-test mapping
scripts/build_bids_v3.py: no requirement-to-test mapping
scripts/fitness_functions.py: REQ-ADS-NFR-QA-007 has no concrete evidence test
src/app/pipeline.py: REQ-ADS-NFR-QA-005 has no concrete evidence test
src/compliance/content_rules.py: no requirement-to-test mapping
src/selector/context.py: no requirement-to-test mapping
test/offline/test_v3_prompt.py: changed test has no requirement-specific coverage mapping
```

这是治理和追踪矩阵缺口，不是 V3 功能测试失败。需要补齐需求到测试/证据的映射，并完成具名人类批准。

状态：`DEFERRED / OPEN · GOVERNANCE FIX REQUIRED`

## 4. 剩余工作

- video demo 录制；
- 最终 run-manifest、checksums 和 evidence 索引；
- 最终测试文档提交；
- Gate 1 mapping/approval 处理，当前保持 `DEFERRED / FAIL`；
- family/gamer 两条 CLI 审计 `detail` 的独立录像；
- 更广泛的人类标注 live corpus（不属于本次闭环）。

## 5. 当前验收判定

```text
V3 Environment: PASS
V3 Test Collection: PASS
V3 Data Integrity: PASS
V3 Core Functional Tests: PASS（49 项）
V3 Full Regression: PASS（675 项）
V3 V1 Integration: PASS（功能）
V3 V1 Output Contract: FAIL（默认）/ PASS（UTF-8 环境）
V3 V1 Live Prompt: TEST-ONLY PASS_WITH_LIMITATIONS（product default offline）
V3 V2 Integration: PASS
V3 Replay: PASS
V3 Mutation: PASS（33/33）
V3 Static Analysis: PASS（ruff 1613818）
V3 Post-Ruff Regression: PASS（675）
V3 Static Analysis: PASS（ruff/mypy/deps/schema/fitness/repo/safety/audit）
V3 Coverage: RECORDED（86%）
V3 Live Prompt: PASS_WITH_LIMITATIONS
V3 Governance: DEFERRED / FAIL（Gate 1 / mapping gaps）
V3 Video Demo: NOT READY
```

Live prompt evidence is recorded in [V3-Live-Prompt-Semantic-Report.md](V3-Live-Prompt-Semantic-Report.md). Confirmed labels and limitations are in [V3-live-prompt-human-labels.json](V3-live-prompt-human-labels.json).

V1 test-only live evidence is recorded in [V3-V1-Live-Prompt-Semantic-Report.md](V3-V1-Live-Prompt-Semantic-Report.md). Confirmed V1 labels are in [V3-v1-live-prompt-human-labels.json](V3-v1-live-prompt-human-labels.json).
