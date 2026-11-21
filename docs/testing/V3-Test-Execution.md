# V3 测试执行记录

> 状态：TEST_EXECUTION_COMPLETE / DEMO_PENDING / GATE1_DEFERRED
> 初始 Run ID：`v3-20261120-53d37fc-01`
> 修复后 Run ID：`v3-20261120-15cc289-01`
> 当前 Run ID：`v3-20261120-1613818-01`
> 测试日期：2026-11-20
> 分支：`test/v3-validation`
> 原始测试 Commit：`53d37fcf933013af46714a7b29c084e4e07a6696`
> 修复后 Commit：`15cc2895a2ee6c60732a1d8a9a84d384ce009a0d`
> 当前 Commit：`161381887e421a121cd2878fcbf397d42a8ac818`
> Ruff 修复 Commit：`1613818`
> Post-Ruff Run ID：`v3-20261120-1613818-01`
> 来源分支：`origin/v3`
> 环境：Conda `SEProjectV3`
> Python：3.11.18
> Editable Project：`E:\cityu\SE\project\SE_Project-v3-test`
> 当前结论：最终 commit `1613818` 上功能、回归、replay、mutation、静态检查和覆盖率均已完成；6 场景 live relevance 30/30 结构合法，标题诱导和名作对照均 5/5，人工确认 PASS_WITH_LIMITATIONS；仅 video demo、最终 evidence 封装和 Gate 1 处理未完成

## 1. 测试范围

计划覆盖：

- 真实 Steam 语料与 manifest；
- CorpusRepository、投影与确定性 top-K；
- 三档内容分级和年龄兜底；
- V1 `--corpus` 与 V2 竞价结算；
- V1/V2/V3 replay、全量测试、变异验证；
- static/schema/fitness/safety/repo 检查；
- video demo 和 evidence 封装。

本轮已完成环境、数据完整性、V3 核心、全量回归、V1/V2 CLI、三套 replay、mutation、静态检查、覆盖率和 live prompt semantic probe。剩余工作是 video demo、最终 evidence 封装和 Gate 1 治理处理。

## 2. 基线和环境

| 项目 | 值 | 结果 |
|---|---|---|
| 测试分支 | `test/v3-validation...origin/v3` | PASS |
| 原始 HEAD | `53d37fcf933013af46714a7b29c084e4e07a6696` | 基线 |
| 修复后 HEAD | `15cc2895a2ee6c60732a1d8a9a84d384ce009a0d` | PASS |
| 工作区 | clean | PASS |
| Conda 环境 | `SEProjectV3` | PASS |
| Python | 3.11.18 | PASS |
| Editable Project | `SE_Project-v3-test` | PASS |
| 模块来源 | app/corpus/compliance/bidding 均在 V3 | PASS |
| V1/V2 sys.path 污染 | False / False | PASS |
| 测试收集 | 675 | PASS |
| collection exit code | 0 | PASS |
| Manifest 修复 commit | `15cc289` | PASS |
| 修复后 Run ID | `v3-20261120-15cc289-01` | PASS |

## 3. 执行结果

| ID | 检查项 | 结果 | 证据 |
|---|---|---|---|
| V3-ENV-001 | Conda、Python、editable install | PASS | `00-environment/` |
| V3-ENV-002 | V1/V2/V3 模块隔离 | PASS | `module-paths.txt` |
| V3-COL-001 | 测试收集 | PASS，675 | `02-collect/pytest-collect.stdout.txt` |
| V3-DATA-001 | items.jsonl 与 manifest SHA-256 | PASS（本地修复后） | manifest 更新为 `5c2110d6...` |
| V3-DATA-002 | tags.jsonl 与 manifest SHA-256 | PASS（本地修复后） | manifest 更新为 `88a9ce9f...` |
| V3-DATA-003 | manifest rows | PASS，5000 | `manifest.json` |
| V3-DATA-004 | bids sidecar 数量 | PASS，5000 | `data/bids-corpus.json` |
| V3-DATA-005 | bid/budget 关系 | PASS，异常 0 | 5000 条 sidecar |
| V3-DATA-006 | 最小出价 | PASS，1 分 | `bids-corpus.json` |
| V3-DATA-007 | corpus 专项 pytest | PASS（本地修复后，22 项） | `03-data/corpus-fixed.junit.xml` |
| V3-DATA-008 | 深度语料统计 | PASS（复核） | 5,000 / 5,000；空 genres 34；age>=13 715；无重复、无缺标签、无 description_clean |
| V3-EOL-001 | Windows 换行诊断 | PASS | `i/lf w/lf`，LF 归一化 hash 仍不匹配 |
| V3-CORE-001 | V3 核心专项测试 | PASS，49 项 | `04-v3-core/v3-core.junit.xml` |
| V3-L3-001 | CorpusRepository 与 Ad 投影 | PASS（包含在 core 49） | `test_corpus.py` |
| V3-L4-001 | 确定性与 top-K | PASS（包含在 core 49） | `test_corpus.py::test_select_*` |
| V3-L5-001 | 内容分级与年龄兜底 | PASS（包含在 core 49） | `test_v3_compliance.py` |
| V3-COMP-001 | 内容分级矩阵 | PASS（核心测试覆盖） | `test_v3_compliance.py` |
| V3-FULL-001 | 全量 pytest | PASS，675 项 | `06-full-regression/offline-full.junit.xml`，0 failed / 0 error |
| V3-V1-001 | V1 corpus 正常端到端 | PASS | exit=0，kind=ad，ad_id=ad_16120，audit=1 |
| V3-V1-002 | V1 非法场景端到端 | PASS | exit=0，kind=no_ad，reason=scene_invalid，audit=1 |
| V3-V1-PERF-001 | V1 内部 load/select/project | PASS | 0.235s / 0.264s / 0.240s，均 < 500ms |
| V3-V1-PERF-002 | V1 CLI 端到端耗时 | OBSERVED | 1.029s，包含 Windows 进程启动/重定向 |
| V3-V1-ENC-001 | V1 stdout 默认编码 | FAIL | 默认文件是 GBK/CP936；UTF-8 解码在 byte 0xd4 失败 |
| V3-V1-ENC-002 | V1 stdout UTF-8 环境重跑 | PASS | `PYTHONIOENCODING=utf-8`，exit=0，JSON 可解析，audit=1 |
| V3-V2-001 | V2 corpus 正常竞价 | PASS | `ad_2993780`，bid=300，price=300 |
| V3-V2-002 | V2 request_id 幂等重放 | PASS | stdout hash 一致，audit 数不增加 |
| V3-V2-003 | V2 新请求继续扣预算 | PASS | `v3-r2` 正常新增 request |
| V3-V2-004 | V2 request_id 场景冲突 | PASS | `no_ad / request_conflict` |
| V3-V2-005 | V2 预算账实一致 | PASS | total=6000，spent=600，remaining=5400 |
| V3-REPLAY-001 | V1 replay | PASS | MUST_PASS 11/11，MUST_FAIL 14/14，p95=0.0033s |
| V3-REPLAY-002 | V2 replay | PASS | 18 cases，positive=4，negative=14，violations=0 |
| V3-REPLAY-003 | V3 replay | PASS | 14/14，violations=0，p95=3.4ms |
| V3-MUT-001 | mutation | PASS，33/33 | `10-mutation/mutation.stdout.txt`，所有变异均被检出 |
| V3-STATIC-RUFF-001 | Ruff | PASS（修复 commit `1613818`） | `ruff check` 返回 0 |
| V3-STATIC-MYPY-001 | mypy | PASS | `11-static/mypy.stdout.txt` |
| V3-STATIC-DEPS-001 | dependency check | PASS | `11-static/dependencies.stdout.txt` |
| V3-STATIC-SCHEMA-001 | requirements schema | PASS | `11-static/schema.stdout.txt` |
| V3-STATIC-FIT-001 | fitness functions | PASS | `11-static/fitness.stdout.txt` |
| V3-STATIC-REPO-001 | repository completeness | PASS | `11-static/repository-completeness.stdout.txt` |
| V3-STATIC-SAFETY-001 | safety paths | PASS | `11-static/safety-paths.stdout.txt` |
| V3-STATIC-AUDIT-001 | implementation audit | PASS | `11-static/implementation-audit.stdout.txt` |
| V3-POST-RUFF-001 | Post-Ruff 全量回归 | PASS，675 项，0 failed / 0 error | `12-post-ruff/offline-full.junit.xml` |
| V3-POST-RUFF-002 | Post-Ruff mutation | PASS，33/33 | `12-post-ruff/mutation.stdout.txt` |
| V3-GOV-AIUSE-001 | AI-use log | PASS | `13-governance/ai-use-log.stdout.txt` |
| V3-GOV-SEMANTIC-001 | Semantic eval | PASS | `13-governance/semantic-eval.stdout.txt` |
| V3-GOV-TESTAPPROVAL-001 | Test approval | DEFERRED / FAIL，7 项映射/证据缺口 | `13-governance/test-approval.stdout.txt` |
| V3-FINAL-RUFF-001 | Final Ruff | PASS | `14-final-static/ruff.stdout.txt` |
| V3-FINAL-MYPY-001 | Final mypy | PASS | `14-final-static/mypy.stdout.txt` |
| V3-FINAL-DEPS-001 | Final dependencies | PASS | `14-final-static/dependencies.stdout.txt` |
| V3-FINAL-SCHEMA-001 | Final requirements Schema | PASS | `14-final-static/schema.stdout.txt` |
| V3-FINAL-FIT-001 | Final fitness | PASS | `14-final-static/fitness.stdout.txt` |
| V3-FINAL-REPO-001 | Final repo completeness | PASS | `14-final-static/repository-completeness.stdout.txt` |
| V3-FINAL-SAFETY-001 | Final safety paths | PASS | `14-final-static/safety-paths.stdout.txt` |
| V3-FINAL-AUDIT-001 | Final implementation audit | PASS | `14-final-static/implementation-audit.stdout.txt` |
| V3-COV-001 | V3 new module coverage | RECORDED，86% total | `15-coverage/v3-coverage.xml` |
| V3-LIVE-PROMPT-001 | Single-scene live baseline | HISTORICAL PASS | 20/20 structural；5/5 title bait；5/5 known title；由多场景最终结果取代 |
| V3-LIVE-PROMPT-002 | Multi-scene live semantic probe | PASS_WITH_LIMITATIONS | 6 scenes × 5 runs，30/30 structural；5/5 + 5/5 adversarial；人工确认 |
| V3-DEMO-001 | video demo | PENDING | 等待测试结束 |

## 4. HANDOVER-V3 对照

| Handover 条目 | 当前状态 | 说明 |
|---|---|---|
| 1 V1 corpus 正常路径 | PASS（性能观察） | 返回 `ad_16120`，候选 30；CLI 观测 1.029s，内部处理约 0.24s |
| 2/3 family/gamer 审计 detail | 部分覆盖 | `test_v3_compliance.py` 覆盖三档规则；尚未单独录制两条 V1 CLI 的 audit detail |
| 4 非法 `--time-slot day` | PASS | `no_ad / scene_invalid`，audit=1 |
| 5 V2 auction | PASS | `ad_2993780`，bid=price=300 |
| 6 request_id 幂等 | PASS | stdout hash 一致，无二次扣费 |
| 7 新 request_id 跨请求预算 | PASS | total=6000，spent=600，remaining=5400 |
| 8 同 request_id 换场景 | PASS | `no_ad / request_conflict` |
| 9 V3 eval | PASS | 14/14，违规 0，p95=3.4ms |
| 10 full pytest | PASS（数量差异） | 实际 675，不是 handover 的 671；已按实际 commit 记录 |
| 11 mutation | PASS | 33/33 |
| 提示词语义质量清单 | V2 PASS_WITH_LIMITATIONS；V1 NOT APPLICABLE | V2 已完成 6 场景 live probe；V1 按设计为 offline-only |

Handover 的主要运行路径和安全边界已遵守；family/gamer 审计 detail 的独立 CLI 录像和真实模型语义质量仍属于未覆盖项，不能声称全部执行。

## 5. 失败详情

### V3-DATA-001 / V3-DATA-002

实际工作区文件：

```text
items.jsonl SHA-256 = 5c2110d6d2f7a1bdc2140d8edbb9ecbea768fb8c8dba3734e575ca45a62eab0d
tags.jsonl  SHA-256 = 88a9ce9f35c828b5f4b4271f8b74c58cee7b4b957b21b4d9d404fb6c81fc58c7
```

manifest 记录：

```text
items.jsonl SHA-256 = 1ac42a497d024a9882ea1ed6d1506295278db29ea807e28b4ae3051076302e61
tags.jsonl  SHA-256 = 56b242b58baaa13260b2455eaeb29fb464ef22aa47d9a49160cc8c5f33f9b267
```

Corpus 专项测试原始失败：

```text
PYTEST_EXIT_CODE=1
FAILED test/offline/test_corpus.py::test_subset_manifest_matches_committed_files
AssertionError: items.jsonl 与 manifest 记录不一致
```

当前已确认不是 Windows CRLF：

```text
git diff --exit-code data/corpus/items.jsonl data/corpus/tags.jsonl = 0
git ls-files --eol = i/lf w/lf（两份文件）
ITEMS_RAW = ITEMS_LF = 5c2110d6...
TAGS_RAW  = TAGS_LF  = 88a9ce9f...
```

因此当前提交中的语料文件与 manifest 记录的 SHA-256 不一致，属于 V3 数据完整性缺陷，而不是测试机换行转换造成的差异。

### 修复验证

团队确认 `items.jsonl` 和 `tags.jsonl` 是最终数据。manifest 只更新了两个 hash 字段，没有修改语料、测试或 composition：

```text
items_sha256: 1ac42a49... -> 5c2110d6...
tags_sha256:  56b242b5... -> 88a9ce9f...
```

修复后 corpus 专项测试结果：

```text
PYTEST_EXIT_CODE=0
22 tests passed
```

### V3-CORE-001

修复 commit `15cc289` 上的新 Run：

```text
Run ID: v3-20261120-15cc289-01
test_corpus.py          22
test_v3_compliance.py    9
test_v3_pricing.py      12
test_v3_eval.py          2
test_v3_prompt.py        4
合计                    49
V3_CORE_EXIT_CODE=0
结果：49 passed
```

### L3/L4/L5 测试映射

核心 49 项不是只跑 corpus 加载；三层分别由以下测试覆盖：

| 层级 | 覆盖测试 | 结果 |
|---|---|---|
| L3 CorpusRepository / Ad 投影 | `test_corpus.py` 的加载、坏 JSON、缺文件、重复 ID、额外字段、全量投影、AD_SCHEMA、空 genres 兜底、注入文本拦截等 22 项 | PASS |
| L4 确定性与 top-K | `test_select_is_deterministic`、`test_select_orders_by_hits_then_item_id`、`test_select_empty_match_returns_empty`、`test_select_respects_k`、`test_k_upper_bound_rejected` | PASS |
| L5 内容分级与年龄兜底 | `test_v3_compliance.py` 的三档矩阵、warnings 并集、年龄兜底、五步顺序、`policy=None` V1 兼容、规则 fail-closed | PASS |

这些测试包含在 `v3-core.junit.xml` 的 49 项中，不是跳过后补写。

### V3-FULL-001

全量回归第一次执行时，`test_repo_completeness.py::test_checker_passes_on_current_tree` 失败。检查器发现以下文件存在但尚未进入 Git：

```text
docs/testing/V3-Test-Execution.md
docs/testing/V3-Test-Report.md
docs/testing/V3_Test_Plan.md
```

该失败属于测试文档未跟踪导致的仓库完整性阻断，不是 V3 业务代码断言失败。提交文档后使用新 commit 和新的 Run 重跑，结果为：

```text
当前 Run ID: v3-20261120-4d0479f-01
Tests: 675
Failures: 0
Errors: 0
Skipped: 0
Time: 26.024 s
FULL_REGRESSION_EXIT_CODE=0
```

### V3-MUT-001

```text
MUTATION_EXIT_CODE=0
mutations detected: 33/33
```

输出中的 `pytest exit=1` 和 `FAILED test_...` 是变异被注入后反例测试按预期失败，是 mutation check 的成功条件，不是当前未变异代码的失败。

### V3-DATA-008

首次深度统计命令报：

```text
NameError: name 'data' is not defined
```

首次命令传递失败后已使用独立 Python 检查脚本完成复核：5,000 / 5,000，空 genres 34，age>=13 715，无重复、无缺失标签、无 `description_clean`。

## 6. 数据文档差异

`docs/HANDOVER-V3.md` 描述了：

```text
empty genres = 34
required_age >= 13 = 715
```

`data/corpus/manifest.json` 当前记录：

```text
empty_genres = 32
age_gated = 707
```

复核后确认这不是数据缺失：`32/707` 是“入选原因分类后的计数”，不是原始边界总数。demo 条目优先归入 `demo`，因此总 `34/715` 中有一部分不会再计入 `empty_genres` 或 `age_gated` 原因。实际语料结构为：5,000 条、空 genres 34、age>=13 715、无重复 item_id、无缺失标签、无 `description_clean`。

## 7. 证据目录

```text
evidence/v3/
├── v3-20261120-53d37fc-01/
│   ├── 00-environment/
│   ├── 01-source/
│   ├── 02-collect/
│   └── 03-data/
└── v3-20261120-1613818-01/
    ├── 12-post-ruff/
    ├── 13-governance/
    ├── 14-final-static/
    ├── 15-coverage/
    └── 16-live-prompt/
        ├── live-prompt-results.json
        └── live-prompt-multi-scene-results.json
```

`corpus-summary.json` 首次命令失败，后续已通过独立 Python 检查脚本完成复核。

### V1 输出编码复核

正常 V1 stdout 文件可以用 GBK/CP936 解码，但不能用 UTF-8 解码：

```text
file: v1-normal.stdout.json
bytes: 835
error: UnicodeDecodeError at byte 0xd4
GBK_DECODE=OK
CP936_DECODE=OK
```

内部 `load + select + project` 三次分别为 `0.235s / 0.264s / 0.240s`，低于 500ms；CLI 端到端 `1.029s` 包含 Python 启动和 PowerShell 重定向开销。当前阻断点是 stdout 编码，不是内部处理性能。

## 8. 下一步

1. 按当前工作区的 V3 demo 脚本录制 video demo（脚本不在本次文档 commit 中）；
2. 生成最终 run-manifest、checksums 和 evidence 索引；
3. 提交测试文档、live prompt 报告和最终证据；
4. Gate 1 继续保持 `DEFERRED / FAIL`，除非团队补齐 mapping 与 TA-0005。
