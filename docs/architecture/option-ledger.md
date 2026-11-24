# Option Ledger — 被否决的架构选项与重开条件（D2.11，optional）

> **状态**：Draft（团队可自由增删）
> **课程对应**：D2 第 11 件 `[optional]` —— *rejected architectural options and when they should be reconsidered.*
> **编写原则**：每条必须写清**为什么否掉**与**什么条件下应该重开**。
> 只写"否掉了 X"而不写重开条件，等于把决策变成不可复核的教条。

---

## 0. 与 ADR 的分工

| 工件 | 记录什么 |
|---|---|
| `docs/architecture/adr-*.md` | **已采纳**的决策：选了什么、备选是什么、后果、重开触发器 |
| **本文件** | **未采纳**的选项：为什么没选、在什么条件下应该回头再看 |

ADR 里已有 `Re-open triggers` 章节的，本文件**引用而不重复**。

---

## 1. 架构层面的否决（V1 阶段）

### O-01 LLM 直接输出最终广告（不做确定性合规层）

| 项 | 内容 |
|---|---|
| **选项** | 让模型输出 `ad_id`，直接渲染 |
| **为什么不选** | 模型无法给出可审计的拒绝理由；一次幻觉 = 一次合规逃逸。`INV-ADS-001` 要求合规零容忍，模型输出不满足"可判定" |
| **选了替代** | **Guarded Hybrid**（`ADR-001`）：AI 只做建议，`src/compliance/` 做 FINAL AUTHORITY |
| **何时重开** | **永不应重开**。这是安全边界，不是效率权衡 |
| **依据** | `ADR-001` §2、`INV-ADS-001`、`INV-ADS-002` |

### O-02 把合规检查放进 `selector/`

| 项 | 内容 |
|---|---|
| **选项** | 在 LLM 客户端内部完成合规过滤，少一次调用链 |
| **为什么不选** | 破坏 concern cluster 分离（`concern-clusters.md` §0）。合规必须在 AI **之后**且**独立**，否则"AI 与检查器"耦合，检查器随时可能被一起改坏 |
| **选了替代** | `app.pipeline` 编排，`compliance` 为独立元素 |
| **何时重开** | **永不应重开**（结构约束 S2 明确禁止 selector 与 compliance 双向依赖） |
| **依据** | `AGENTS.md` ⑤「绝不允许把 compliance 塞进 selector」；`structural-constraints.md` S2 |

### O-03 重试后展示次优候选

| 项 | 内容 |
|---|---|
| **选项** | 解析失败后放宽 schema，展示"差不多"的结果 |
| **为什么不选** | 使 `INV-ADS-003` 从 fail-closed 变为 fail-open——安全语义反转 |
| **选了替代** | 严格 JSON gate；失败重试 **1 次**，仍失败则 `no_ad` |
| **何时重开** | 需要同时重开 `ADR-001` 触发器 **T2** 并取得人工批准 |
| **依据** | `AGENTS.md` ⑦「需要引入'重试后展示次优候选'→ 停止，重开 ADR-001 T2」 |

### O-04 让 BUILD agent 读测试源码以"对齐实现"

| 项 | 内容 |
|---|---|
| **选项** | 允许 BUILD 读 `test/`，减少来回 |
| **为什么不选** | **blindness invariant ①**：能读测试的实现者会把测试改成匹配其破损实现——测试通过、不变量被违反、无人察觉 |
| **选了替代** | BUILD 只接收 **stripped error report**（失败测试 ID + 断言摘要） |
| **何时重开** | **不可重开**（不可协商） |
| **依据** | `AGENTS.md` ⑥；`permissions.jsonc` `P-008` |

---

## 2. 已经过实测否决的具体方案（2026-11）

这一节是本文件**唯一有实证的部分**，每条都有可复现的实验结果。

### O-05 用 `pyproject.toml` 的 `where = ["src", "."]` 修 Gate 5

> **本节已于 2026-11-25 按 CI 证据改判。** 原始结论「此方案已证伪」是错的，
> 原因是本地对照实验的条件与 CI 不一致（见下表「为什么当时判错」）。
> 保留原始记录以便审计，改判依据逐条列在下方。

| 项 | 内容 |
|---|---|
| **选项** | 让 setuptools 把仓库根也收进 packages find，使 `scripts` 成为可导入的包 |
| **改判结论** | ✅ **CI 实测有效**。`PR #10`（`where = ["src", "."]` + `exclude` 六项）**7/7 全绿**，其中 Gate 5 的 `Install` 与 `Offline test suite` 两步均为 success |
| **决定性对照** | 同时段 `PR #7`（只改 `README.md`，不碰 `pyproject.toml`）的 Gate 5 **仍为 failure**。两者 CI 环境相同、只差这一处改动，故 Gate 5 转绿可归因于 `pyproject.toml` |
| **本地复核（原判）** | 干净 venv 里 `pip install -e ".[dev]"` 后 `import scripts.build_corpus_subset` **成功**（editable finder 的 `MAPPING` 含 `'scripts'`），但当时判定「CI 的 Gate 5 依旧在收集期中断」 |
| **为什么当时判错** | 本地三组对照实验只验证了「安装后能否 `import scripts`」，**没有在 `pip install -e` 之后的同一环境里、从非仓库根目录重跑 pytest**。缺了这关键一步，得出「安装有效性 ≠ 收集期可导入」的结论，并把它当成方案失效的证据。实际上 `pip install -e` 一旦把 `scripts` 注册进 editable finder，pytest 在任意工作目录都能导入它 |
| **何时重开** | 不重开。该结论已被 CI 证据推翻 |
| **教训** | ①「本地装完能 import」不等于「CI 里 pytest 能 import」——但反过来也成立：**本地实验不足以否定一个方案时，应以 CI 实测为准**；②对照实验必须有**单一变量**的同环境对照组（`PR #7` vs `PR #10` 就是），缺对照组的孤立实验容易得出错误结论；③本条目就是「没有对照组就下结论」的实例 |

### O-06 新增 `scripts/__init__.py`

| 项 | 内容 |
|---|---|
| **选项** | 把 `scripts/` 变成常规包 |
| **实测结果** | 在仓库根目录下，有无 `__init__.py` 都能 import（无则 `_NamespacePath`，有则普通 `list`）；在非仓库根目录下，**加不加都仍报 `ModuleNotFoundError`** |
| **为什么不选** | 决定性的变量不是包注册，而是 `sys.path` 是否含仓库根 |
| **何时重开** | 不重开。**此方案已证伪** |

### O-07 用自定义 build-backend 生成 console script 垫片

| 项 | 内容 |
|---|---|
| **选项** | `build-backend = "_spike_backend"` + `backend-path = ["scripts"]`，在 `build_editable` 里生成 `<venv>/Scripts/<name>-script.py` 垫片（`sys.path.insert` + `runpy.run_path`） |
| **实测结果** | 10 个脚本垫片全部生成成功，13 条门禁命令全部 `rc=0`（ruff / mypy / 679 passed / mutation 33/33）。**但 Gate 5 的收集期中断依旧存在** |
| **为什么不选** | 解决了"脚本能不能执行"，没解决"测试能不能 import"；且为一个测试 bug 引入自定义 build backend，复杂度远超收益 |
| **何时重开** | 只有当项目真的需要把 `scripts/` 作为可分发入口发布时才考虑 |

### O-08 在 `ci.yml` 里注入 `PYTHONPATH`

| 项 | 内容 |
|---|---|
| **选项** | 在 Gate 5 的 job 里加 `env: PYTHONPATH: ${{ github.workspace }}` |
| **能不能修** | **能修**。这是最少代码量的方案 |
| **为什么不选** | **"为过门禁而改门禁"**。`.github/workflows/**` 属 `P-011`（requires_approval），且需求是让**测试自身**不依赖工作目录，而不是让 CI 迁就测试 |
| **何时重开** | 若团队认定 Gate 5 修复必须触碰 CI 配置，且已取得人工批准与 ADR 记录 |
| **已被什么替代** | **O-05**（改 `pyproject.toml` 的 `packages.find`）。两者效果等价——都让 `scripts` 可被导入——但 O-05 只动一行构建配置、不触碰 workflow 定义，且已由 `PR #10` 实测 7/7 全绿 |

### O-09 修改 `test/offline/test_corpus.py` 的 import 写法

| 项 | 内容 |
|---|---|
| **选项** | 把 `from scripts.build_corpus_subset import select_subset` 改成相对导入或 `importlib` 动态加载 |
| **为什么不选** | 这是**修改既有测试**。`INV-ADS-011` / `permissions.jsonc` `D-003` 禁止删除或跳过既有测试；改 import 虽不是删测试，但属于改动测试归 TESTER 所有，且需先签 TA |
| **何时重开** | 若 TESTER 角色愿意并已获 TA 批准 |

---

## 3. 产品/演进层面的否决

### O-10 V2 直接替换 V1 的行为（破坏性演进）

| 项 | 内容 |
|---|---|
| **选项** | V2 竞价取代 V1 单广告展示，删除 V1 路径 |
| **为什么不选** | 违反"扩展不删除"（`structural-constraints.md` S2；fitness **V4** 检查既有测试模块不得消失） |
| **选了替代** | V1 / V2 / V3 三代共存，通过配置与入口切换；需求 ID 空间连续（`REQ-…` 追加而非改写） |
| **何时重开** | **不应重开**。删除既有路径会让 V1 的回归证据全部作废 |

### O-11 每个版本重新 seed 预算

| 项 | 内容 |
|---|---|
| **选项** | 演示时清空账本重来，得到"干净的"预算数字 |
| **为什么不选** | **预算是跨请求持久状态**，重新 seed 等于伪造历史花费；`AGENTS.md` V2 段明文禁止 |
| **选了替代** | 演示脚本使用独立数据库文件；同 `request_id` 同输入返回保存响应，不重扣费 |
| **何时重开** | **不应重开** |

### O-12 给 V1/V2 的历史提交补写 PR 评审记录

| 项 | 内容 |
|---|---|
| **选项** | 为 17 个 V1 提交 + 12 个 V2 提交补写"每 PR 一份"的 review memo |
| **为什么不选** | 那些提交**没有 PR 编号、没有 diff 边界、没有评审当时的上下文**。补写出来的"评审"是虚构过程，一旦被追问提交顺序就站不住 |
| **选了替代** | 在 `docs/review-memo.md` 加「评审覆盖说明」如实披露缺口；从有 PR 的那一天起严格执行 |
| **何时重开** | **不应重开**。与 `docs/test-approvals.yaml` 的 `TA-0006` 先例一致（事后确认必须显式承认不满足时序） |

### O-13 把 AI proxy 复核改称"人类评审"

| 项 | 内容 |
|---|---|
| **选项** | 措辞上把 `ai_supervisor` 的角色记为人类评审，让 D4 看起来更完整 |
| **为什么不选** | 课程「No agent may self-approve」；`permissions.jsonc` 写死 `proxy_review_is_human_approval = false` |
| **选了替代** | 保持如实区分；`TD-V2` 系列与 `review-memo` 各段均显式标注参与者类型 |
| **何时重开** | **不应重开** |

---

## 4. 维护约定

1. **新增一条否决时**，必须同时填「何时重开」。填不出重开条件的，说明这不是一个"选项"而是一条"约束"，应写进 `invariants.md` 而不是这里。
2. **方案被证伪时**，不要删条目——把实测结果写进「实测结果」列。**证伪记录本身是资产**。
3. **与 ADR 重叠时**，本文件只写"不选的理由"，细节指向 ADR。

---

## 5. 追溯

| 本文件条目 | 来源 |
|---|---|
| O-01 ~ O-03 | `ADR-001`（Guarded Hybrid）；`ADR-002`；`AGENTS.md` ⑤⑦ |
| O-04 | `AGENTS.md` ⑥「blindness invariant ①」；`permissions.jsonc` `P-008` |
| O-05 ~ O-09 | 2026-11-24 的实验记录（`/tmp/cs5351` 隔离环境；本地实验期间 `pyproject.toml` 曾回滚至 md5 `0a68cbf161952c189db52f9d1c3dcfb6`，后经 `PR #10` 改为 `where = ["src", "."]` 并合入 `main`） |
| O-10 | `structural-constraints.md` S2；`fitness_functions.py` V4 |
| O-11 | `AGENTS.md` V2 段；`ADR-005` |
| O-12 | `docs/review-memo.md`；`docs/test-approvals.yaml` `TA-0006` |
| O-13 | `permissions.jsonc` `v2_authorization.proxy_review_is_human_approval`；课程「No agent may self-approve」 |
