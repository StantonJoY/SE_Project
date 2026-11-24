# Evaluation Logbook — 架构选择的累积证据（D2.9，optional）

> **状态**：Draft（团队可自由增删）
> **课程对应**：D2 第 9 件 `[optional]` —— *the accumulated evidence behind the architecture choices.*
> **编写原则**：**只登记有出处的数字**。每条写清「当时的决策」「支撑它的实测数字」「证据在哪」。
> 数字都标了**它可以复现的命令**；复现不出来的不写进来。

---

## 0. 这份文件与 `review-memo` 的分工

| 工件 | 回答的问题 |
|---|---|
| `docs/review-memo.md` | **某一次交付**做得怎么样（判定 APPROVE / CHANGES REQUIRED） |
| **本文件** | **某个架构决策**当时凭什么这么选（累积证据，不看单次） |

---

## 1. 证据总账（当前基线）

| 指标 | 值 | 复现方式 |
|---|---|---|
| 需求条目 | **61** 条（V1 22 + V2 19 + V3 20） | `python scripts/validate_requirements.py` |
| 不变量 | **36** 条：V1 16 = `INV-ADS-001`..`016`（`docs/architecture/invariants.md` 根小节）+ V2 12 = `INV-V2-001`..`012` + V3 8 = `INV-V3-001`..`008`（后两者在同文件轮次小节） | 逐 id 实测计数 |
| 架构元素 | **9** 个（`src/` 下 ①..⑨：`ads`/`scene`/`compliance`/`selector`/`render`/`audit`/`app`/`bidding`/`corpus`）。`eval/`、`scripts/` **不占元素编号**（`architecture-blueprint.md` 明确列为「验证资产」） | `scripts/fitness_functions.py` `ELEMENT_BY_PACKAGE`（S1） |
| 离线测试 | **679** 个用例 / **31** 个模块 | `pytest test/offline -q` |
| 变异验证 | **33 / 33** 全部被检出 | `python scripts/mutation_check.py` |
| CI 门禁 | **7** 道（Gate 1/2/3/4/5/5b/6） | `.github/workflows/ci.yml` |
| 评估用例 | **57** 条（V1 **25** + V2 **18** + V3 **14**） | `eval/eval_cases.json` / `v2_cases.json` / `v3_cases.json` |
| bidding 语句覆盖 | **≥ 90%**（CI 强制 `--cov-fail-under=90`） | `pytest --cov=src/bidding` |

> 口径来源：`docs/HANDOVER-V3.md`、`AGENTS.md` 顶部 V3 状态块、`README.md` 门禁表。
> **注意**：`README.md` 的 D8 行与门禁表第 5 行曾为旧数字（285 / 86 / 13-13），
> 已于 2026-11-24 经 PR 事实纠错更正为 **679 / 33-33**（D8 行与门禁表第 5 行均已核对）。

---

## 2. 按时间累积的架构证据

### E-01 · 2026-10-06 · 采用 Guarded Hybrid（AI 建议 + 代码裁决）

| 项 | 内容 |
|---|---|
| **决策** | 模型只做候选集内的建议；`src/compliance/` 五步确定性管道是 FINAL AUTHORITY |
| **为什么需要证据** | 这是整个项目的核心架构承诺，需要证明"AI 不会被信任到危险的程度" |
| **支撑证据** | ① 合规管道任一失败即 REJECT → `no_ad`（fail-closed）；② 评估集 25 条里违规逃逸 = 0（`ADR-003` 的分母分离口径） |
| **证据位置** | `ADR-001`、`ADR-002`、`eval/eval_cases.json`、`INV-ADS-001`/`002` |
| **之后被证伪过吗** | 否。V2 与 V3 都在此前提下扩展，未改动权威边界 |

### E-02 · 2026-10-06 · 失败语义全项目统一为 fail-closed

| 项 | 内容 |
|---|---|
| **决策** | 16 条运行时失败策略（`RP-001`~`016`）全部 fail-closed |
| **支撑证据** | 每条策略都有对应的降级路径实现与测试；违规数 = 0 |
| **证据位置** | `docs/architecture/runtime-policy-catalog.md`、`test/offline/` |
| **未完成** | `BUG-007` 发现 `BannedWords.load()` 姿态漂移，说明"统一"并非一开始成立——是**发现问题后补统一**的（`TD-014` 仍未关闭） |

### E-03 · 2026-10-06 · 评估集作为一等架构资产

| 项 | 内容 |
|---|---|
| **决策** | 评估集本身受保护（`P-009`），改判据须 ADR |
| **支撑证据** | 改判据以通过判据 = 掩盖而非失败（`.agent/rules.md` R2）；`eval/**` 从可自由改变为需 ADR |
| **证据位置** | `ADR-003`、`ADR-004`、`permissions.jsonc` `P-009` |
| **实证** | 门禁 4 在每次 prompt/model 变更时 replay 固定评估集 |

### E-04 · 2026-11-04 · V1 验证平面的证据固化

| 项 | 内容 |
|---|---|
| **决策** | 把门禁运行输出、依赖快照、diff stat 作为**文件**存进 `evidence/v1/` |
| **支撑证据** | 两个证据批次：`v1-20261104-a31860f-01` / `-02`，含 `actual-diff-stat.txt`、`actual-status.txt`、`ad014-compliance.stdout.txt`、`conda-explicit.txt`、`current-code-changes.patch` 等 |
| **证据位置** | `evidence/v1/` |

### E-05 · 2026-11-05 · V2 竞价采用 `relevance × bid` + pay-as-bid

| 项 | 内容 |
|---|---|
| **决策** | 单赢家；`relevance * bid` 排序、`ad_id` 平局、`pay_as_bid` 计价；预算/结果/审计**同事务**提交 |
| **支撑证据** | ① 三档通过率 **21 / 10 / 24**；② 延迟分解；③ 预算 **6000 → 5100**（真实调用，扣费正确）；④ 请求重放不重扣费；⑤ 医疗品类 `ad_009` 打 **85** 分仍被 `no_ad` / `compliance_rejected`，**扣 0**（2.454s）——证明合规在扣费之前 |
| **证据位置** | `docs/review-memo.md`「CityU 真实调用与本地钩子复核（2026-11-05）」；`ADR-005` |
| **这条最有说服力** | 它是**真实模型 + 真实扣费**的端到端证据，且演示了"模型说好、合规说不"的权威边界 |

### E-06 · 2026-11-05 · V2 回归基线

| 项 | 内容 |
|---|---|
| **决策** | 合并前必须全量重跑前几轮测试，零回归 |
| **支撑证据** | 本地技术复核 **614** 项通过；上线前暂存预演 **617** 项通过；bidding 覆盖 **95.59%**；变异 **25** 项均检出（当时基线） |
| **之后的变化** | V3 后上升到 **679** 项 / 变异 **33** 项——**说明基线在增长而非替换** |
| **证据位置** | `docs/review-memo.md`「本地技术复核记录」「上传前暂存预演」 |

### E-07 · 2026-11-22 · V3 接入真实语料（第 9 个架构元素）

| 项 | 内容 |
|---|---|
| **决策** | 新增 `src/corpus/` 作为第 ⑨ 个元素；不修改既有 8 个元素的契约 |
| **支撑证据** | ① 679 测试全绿；② 33/33 变异；③ S1 结构门确认"一元素一模块"仍成立（9 个）；④ PR #3 走了**完整的 PR 流程**（21 提交，merge `8b5a17a`） |
| **独立测试发现的 8 个问题** | `F-001` manifest 哈希被 CRLF 破坏、`F-004`、`F-006`、`F-007`（13 项 lint）、`F-008`（门禁 1 映射缺口）等 |
| **证据位置** | `docs/review-memo.md`「V3 复核记录」；`ADR-006` |
| **注意** | 判定是 **ACCEPTED WITH DOCUMENTED GAP**——不是无条件通过。`TD-018` 未关闭 |

### E-08 · 2026-11-22 · 分支保护启用并实测

| 项 | 内容 |
|---|---|
| **决策** | `main` 启用分支保护：6 道必需 check + `require_code_owner_reviews = true` + `required_approving_review_count = 0` |
| **支撑证据** | 同一账号、同一命令、只改设置的三段对照：<br>① 开启前 → 直推成功；<br>② 开启、无 bypass → **被拒** `! [remote rejected] main -> main (push declined due to repository rule violations)`，`6 of 6 required status checks are expected`；<br>③ 加入 bypass 后 → 成功（提示仍在，放行） |
| **证据位置** | `docs/branch-protection.md` §9.1 / §9.3 |
| **这条为什么有价值** | 保护不是"配了就算"，而是**有实证的状态转换** |

### E-09 · 2026-11-24 · Gate 5 根因定位（`scripts` 不可导入）

> **本条已于 2026-11-25 修正结论。** 原始结论「与包注册无关」被 `PR #10` 的 CI 证据推翻，
> 过程记录保留在下方，供复盘「孤立实验为什么不可靠」。

| 项 | 内容 |
|---|---|
| **问题** | CI 的 Gate 5 在收集期中断：`test/offline/test_corpus.py:50: from scripts.build_corpus_subset import select_subset` → `ModuleNotFoundError: No module named 'scripts'`，exit 2 |
| **三组对照实验**（同一环境、同一份原版 `pyproject.toml`） | ① 仓库根跑 → **23 passed**；② 在 `/tmp` 用绝对路径跑 → **ModuleNotFoundError**；③ 在 `test/` 目录内跑 → **ModuleNotFoundError** |
| **隔离实验发现** | pytest 把 rootdir 插进 `sys.path[1]`（`sys.path[0]` 是 rootdir 下的测试目录）；`scripts` 有无 `__init__.py` 都能在 rootdir 场景导入（无则 `_NamespacePath`，有则普通 `list`） |
| **原结论（已推翻）** | ~~能否 import `scripts` 取决于 pytest 的 rootdir → `sys.path` 注入，与包注册无关~~ |
| **修正后的结论** | **与包注册有关。** `pyproject.toml` 的 `where = ["src", "."]` 让 `pip install -e` 把 `scripts` 注册进 editable finder，之后 pytest 在任意工作目录都能导入它 |
| **推翻它的证据** | `PR #10`（只改 `pyproject.toml` 两行：`where = ["src", "."]` + `exclude`）→ **7/7 全绿**，Gate 5 的 `Install` 与 `Offline test suite` 均 success；同一时段 `PR #7`（只改 `README.md`）→ Gate 5 **仍为 failure**。单一变量的同环境对照 |
| **原实验为什么不够** | 三组对照都在**未安装**或**安装后未重跑**的条件下做，只测了「rootdir 注入」，没测「editable finder 注册」这条路径。缺对照组即下结论，是本仓库一次真实的实验方法论失误 |
| **实测排除的方案** | ✅ 仍成立：新增 `scripts/__init__.py`（非仓库根下仍失败）；自定义 build-backend 生成垫片（13 条门禁全绿但 Gate 5 仍红）。❌ 已推翻：`where=["src","."]` |
| **证据位置** | 本文件、`option-ledger.md` O-05~O-09；`PR #10` 的 CI 日志（run `45413980410`）；`main` 的 `pyproject.toml`（blob `ce09bb78…`，`where = ["src", "."]` + 六项 `exclude`） |
| **状态** | ✅ **已修复并已合入 `main`**（`PR #10` merge commit `d67ed09c`，2026-11-24T17:03:57Z） |

---

## 3. 怎么用这份日志

1. **做架构决策前**：来这里看有没有同类证据。没有就说明这个决策目前是**无证据的**，应登记进 `risk-list.md`。
2. **被问到"为什么这么设计"时**：直接指到某条 `E-xx` 的证据位置。
3. **证据过期时**：不要删，加一行「之后的变化」。证据的时间性本身就是信息。

---

## 4. 待补的证据（已知缺口）

| 缺口 | 为什么重要 | 阻塞原因 |
|---|---|---|
| **运行时 monitor 输出** | `trace-matrix.md` 的 22 条 monitor 是"可观测性"这一节的核心证据，目前没有采集输出 | `RW-01` 需先签 `TA-0008` |
| **p95 延迟与成本测量** | `NFR-PERF-001` / `NFR-COST-001` 的 fit criterion 需要实测数字 | V2 段 README 自述"p95 和成本测量仍待完成" |
| **PR 路径的保护验证** | 只改 `docs/` 的 PR 免批准可合 / 改 `src/` 需 owner 批准 | `RW-15`，需人类开 2 个 PR |
| ~~**Gate 5 修复后的全绿基线**~~ | ~~当前所有 PR 都卡在 Gate 5，没有一次完整绿的 CI 记录~~ | ✅ **已闭合（2026-11-24）**：`PR #10`（`pyproject.toml` 修复）**7/7 全绿**；`PR #12` 修复后同样全绿 |

---

## 5. 追溯

| 条目 | 来源 |
|---|---|
| §1 总账 | `docs/HANDOVER-V3.md`；`AGENTS.md` V3 状态块；`eval/*.json` 实测计数 |
| E-01 / E-02 | `ADR-001`、`ADR-002`、`runtime-policy-catalog.md` |
| E-03 | `ADR-003`、`ADR-004`、`permissions.jsonc` `P-009` |
| E-04 | `evidence/v1/` 目录实测 |
| E-05 / E-06 | `docs/review-memo.md`「CityU 真实调用与本地钩子复核」「本地技术复核记录」「上传前暂存预演」 |
| E-07 | `docs/review-memo.md`「V3 复核记录」；`ADR-006`；PR #3 |
| E-08 | `docs/branch-protection.md` §9 |
| E-09 | 2026-11-24 的隔离环境实验；`option-ledger.md` O-05~O-09 |
