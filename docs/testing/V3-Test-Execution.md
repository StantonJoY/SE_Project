# V3 测试执行记录

> 状态：CORE_TESTS_PASS / FULL_REGRESSION_BLOCKED_BY_TRACKING
> 初始 Run ID：`v3-20261120-53d37fc-01`
> 修复后 Run ID：`v3-20261120-15cc289-01`
> 测试日期：2026-11-20
> 分支：`test/v3-validation`
> 原始测试 Commit：`53d37fcf933013af46714a7b29c084e4e07a6696`
> 修复后 Commit：`15cc2895a2ee6c60732a1d8a9a84d384ce009a0d`
> 来源分支：`origin/v3`
> 环境：Conda `SEProjectV3`
> Python：3.11.18
> Editable Project：`E:\cityu\SE\project\SE_Project-v3-test`
> 当前结论：环境 PASS；测试收集 PASS；manifest 元数据修复已验证；V3 核心 49 项 PASS；全量回归被 3 个未跟踪的 V3 测试文档阻断；业务回归结论待重跑

## 1. 测试范围

计划覆盖：

- 真实 Steam 语料与 manifest；
- CorpusRepository、投影与确定性 top-K；
- 三档内容分级和年龄兜底；
- V1 `--corpus` 与 V2 竞价结算；
- V1/V2/V3 replay、全量测试、变异验证；
- static/schema/fitness/safety/repo 检查；
- video demo 和 evidence 封装。

当前已完成环境和测试收集、数据 hash 校验、manifest 修复、V3 核心专项测试，并开始全量回归。全量回归当前被未跟踪的 V3 测试文档阻断。

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
| V3-COMP-001 | 内容分级矩阵 | PASS（核心测试覆盖） | `test_v3_compliance.py` |
| V3-V1-001 | V1 corpus 端到端 | PENDING | 等待 V1/V2 集成阶段 |
| V3-V2-001 | V2 定价与竞价 | PENDING | 等待 V1/V2 集成阶段 |
| V3-REPLAY-001 | V1/V2/V3 replay | PENDING | 等待核心与回归测试 |
| V3-FULL-001 | 全量 pytest | FAIL（未跟踪文档） | repo completeness 检出 3 个 V3 测试文档未入库 |
| V3-MUT-001 | mutation 33/33 | PENDING | 等待核心测试 |
| V3-DEMO-001 | video demo | PENDING | 等待测试结束 |

## 4. 失败详情

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

### V3-FULL-001

修复后 Run 执行全量测试时，`test_repo_completeness.py::test_checker_passes_on_current_tree` 失败。检查器发现以下文件存在但尚未进入 Git：

```text
docs/testing/V3-Test-Execution.md
docs/testing/V3-Test-Report.md
docs/testing/V3_Test_Plan.md
```

该失败属于**测试文档未跟踪导致的仓库完整性阻断**，不是 V3 业务代码断言失败。文档提交后必须用新 commit 和新 Run 重新执行全量测试。

### V3-DATA-008

首次深度统计命令报：

```text
NameError: name 'data' is not defined
```

首次命令传递失败后已使用独立 Python 检查脚本完成复核：5,000 / 5,000，空 genres 34，age>=13 715，无重复、无缺失标签、无 `description_clean`。

## 5. 数据文档差异

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

## 6. 证据目录

```text
evidence/v3/v3-20261120-53d37fc-01/
├── 00-environment/
│   ├── python-version.txt
│   ├── python-prefix.txt
│   ├── pip-show-ad-recommender.txt
│   └── module-paths.txt
├── 01-source/
│   ├── git-branch.txt
│   ├── git-commit.txt
│   ├── git-status.txt
│   └── git-remote.txt
├── 02-collect/
│   └── pytest-collect.stdout.txt
└── 03-data/
    ├── corpus.junit.xml
    ├── corpus.stdout.txt
    ├── corpus.stderr.txt
    ├── corpus-summary.json
    ├── corpus-fixed.junit.xml
    ├── corpus-fixed.stdout.txt
    └── corpus-fixed.stderr.txt
```

`corpus-summary.json` 首次命令失败，后续已通过独立 Python 检查脚本完成复核。

## 7. 下一步

1. 将更新后的三份 V3 测试文档复制到 V3 worktree 并提交；
2. 用新 commit 创建新的修复后 Run ID；
3. 重新执行全量 pytest；
4. 执行 V1/V2 端到端、replay 和 mutation；
5. 最后进行 video demo 和 evidence 封装。
