# V3 执行计划（Execution Plan）· 真实语料接入

> **状态**：草案待人工批准（批准前禁止写代码）
> **依据**：`docs/req/requirements-v3-se.md`（20 条需求）、`V3spike结论.md`（可行性实测）、
> `docs/plans/V2-execution.md`（先例：PR 分阶段 + 人工评审卡点）
> **编号**：需求以 `requirements-v3-se.md` 的**草案标签**引用，正式 ID 在 PR-0 录入时确定

---

## ① Traceability

```yaml
task_id: "V3-CORPUS"
title: "用 Steam 真实语料替换手写素材，并扩展确定性内容分级"
requirements_draft:
  - REQ-V3-SE-01 .. REQ-V3-SE-15        # 见 docs/req/requirements-v3-se.md
requirements_registry:                  # PR-0 录入后的正式 ID
  - REQ-ADS-FR-009 / FR-010 / FR-011
  - REQ-ADS-ARCH-013 / ARCH-014 / ARCH-015
  - REQ-ADS-NFR-SAFETY-008 / 009 / 010
  - REQ-ADS-NFR-COST-002
  - REQ-ADS-SEC-003
  - REQ-ADS-NFR-QA-005 / 006 / 007
  - REQ-ADS-GOV-004 / 005
  - REQ-ADS-FR-012（广告费 = 定价 × 5%）/ REQ-ADS-ARCH-016（派生规则唯一来源）
invariants:
  - "INV-ADS-001（compliance 不可绕过）—— 必须保持"
  - "INV-V3-001 语料不进 Ad 契约（新增）"
  - "INV-V3-002 候选生成确定性且无状态（新增）"
  - "INV-V3-003 内容并集判据必拦截（新增）"
  - "INV-V3-004 年龄兜底必拦截（新增）"
  - "INV-V3-005 权威链顺序不变（新增）"
  - "INV-V3-006 语料文本不可信（新增）"
test_design: "pytest 离线确定性（MockLLM）+ 5,000 条真实语料子集作为只读夹具；无网络、无临时目录"
```

**自检**：草案标签在录入前**不是**注册表 ID，`validate_requirements.py` 不认它——
所以 PR-0 必须先落地，PR-1 才能引用正式 ID。

---

## ② Interface Contract

```yaml
elements:
  - file: "src/corpus/__init__.py"
    exports: ["CorpusRepository", "CorpusItem", "corpus_to_ad", "select_candidates", "CorpusLoadError"]

  - file: "src/corpus/models.py"
    class: "CorpusItem"
    fields: {item_id: int, name: str, genres: list[str], native_tags: list[str], summary: str,
             required_age: int, content_descriptors: list[int], content_warnings: list[str], tags: dict}
    note: "**不持有 description_clean**（REQ-V3-SE-01）"

  - file: "src/corpus/repository.py"
    class: "CorpusRepository"
    public_methods:
      - name: "load"
        params: {items_path: "str | Path", tags_path: "str | Path"}
        returns: "CorpusRepository"
        raises: ["CorpusLoadError"]
      - name: "all"
        returns: "list[CorpusItem]"

  - file: "src/corpus/projection.py"
    function: "corpus_to_ad"
    params: {item: "CorpusItem"}
    returns: "tuple[Ad, CorpusFacts]"
    note: "返回 Ad（过 AD_SCHEMA）+ 旁路事实；ad_id = f'ad_{item_id}'"

  - file: "src/corpus/select.py"
    function: "select_candidates"
    params: {scene: "Scene", items: "list[CorpusItem]", mapping: "dict[str, list[str]]", k: "int"}
    returns: "list[str]"
    note: "纯函数：命中数降序 + item_id 升序，取前 K"

  - file: "src/corpus/pricing.py"
    functions:
      - name: "bid_cents_from_price"
        params: {price_cents: "int"}
        returns: "int"
        note: "max(1, round(price_cents * 0.05))；5% 系数**只允许**出现在此文件"
      - name: "budget_cents_for"
        params: {bid_cents: "int", impressions: "int = 20"}
        returns: "int"
        note: "bid_cents * impressions；保证整数、>= bid_cents"

  - file: "scripts/build_bids_v3.py"
    function: "build_bids"
    params: {corpus: "CorpusRepository", out_path: "Path"}
    returns: "None"
    note: "调用 pricing 生成 data/bids-corpus.json；幂等，重跑结果逐字节一致"

  - file: "src/app/pipeline_v2.py"            # V2 编排层，受 ADR-005 保护
    changes:
      - "run_compliance(..., facts=corpus_facts)  —— 把语料内容事实传进合规"
    note: "竞价/账本逻辑零改动；仍要求 compliance 在结算之前"

  - file: "src/compliance/pipeline.py"        # 唯一被修改的冻结层
    changes:
      - "run_compliance(..., facts: Mapping[str, CorpusFacts] | None = None)"
      - "check_scene(ad, scene, rules, facts=None)"
    note: "五步顺序与既有 4 个 check_* 签名不变"
```

**依赖方向**：`corpus` 只能被 `app` 导入；`corpus` 不得 import `selector`/`compliance`/`audit`（由 fitness S1/S2 强制）。

---

## ③ Scope Boundaries

```yaml
target_files_pr1: ["src/corpus/*.py", "config.yaml", "test/offline/test_corpus*.py"]
target_files_pr2: ["src/compliance/pipeline.py", "data/scene-content-rules.yaml",
                   "test/offline/test_v3_compliance*.py"]
target_files_pr3: ["src/corpus/pricing.py", "scripts/build_bids_v3.py", "data/bids-corpus.json",
                   "src/app/pipeline_v2.py", "test/offline/test_v3_pricing*.py"]
target_files_pr4: ["scripts/fitness_functions.py", "docs/architecture/*.md",
                   "docs/req/requirements.yaml", "eval/*", "docs/ai-use-log.yaml"]
target_files_pr0: ["docs/req/requirements.yaml", "docs/architecture/adr-006-*.md",
                   "docs/architecture/invariants.md", "docs/code-governance/acceptance-coverage-map.yaml"]
allowed_imports: ["json", "pathlib", "dataclasses", "typing", "collections.abc", "yaml"]
prohibited_imports: ["requests", "urllib", "random", "time", "audit", "selector", "compliance"]
data_access: "只读 demo_steam_30 派生的仓库内子集；audit 只写不读"
frozen_paths_not_touched: ["src/ads/", "src/scene/", "src/selector/", "src/bidding/"]
```

**触及的受保护路径**（`check_safety_paths.py --show-paths`）：
`src/compliance/`、`data/`、`eval/`、`src/app/pipeline_v2.py`、`scripts/fitness_functions.py`、`docs/req/requirements.yaml`、
`docs/code-governance/acceptance-coverage-map.yaml` → **全部由 PR-0 的 `ADR-006` 覆盖**。

---

## ④ Testing Strategy

```yaml
cases:
  # 语料与投影
  - {name: "test_corpus_load_30_items", criterion: "REQ-V3-SE-01", type: unit}
  - {name: "test_corpus_does_not_hold_long_text", criterion: "REQ-V3-SE-01", type: negative}
  - {name: "test_projection_passes_ad_schema_all_30", criterion: "REQ-V3-SE-02", type: unit}
  - {name: "test_raw_corpus_item_rejected_by_ad_schema", criterion: "REQ-V3-SE-02", type: negative}
  - {name: "test_projection_empty_genres_fallback", criterion: "REQ-V3-SE-03", type: negative}
  # 候选生成
  - {name: "test_candidate_selection_deterministic", criterion: "REQ-V3-SE-04", type: deterministic_replay}
  - {name: "test_candidate_selection_empty_match", criterion: "REQ-V3-SE-04", type: negative}
  - {name: "test_token_budget_rejects_k_over_50", criterion: "REQ-V3-SE-05", type: negative}
  # 合规
  - {name: "test_pipeline_step_order_unchanged", criterion: "REQ-V3-SE-06", type: unit}
  - {name: "test_cs2_rejected_in_family_scene", criterion: "REQ-V3-SE-07", type: negative}
  - {name: "test_among_us_rejected_by_warnings_union", criterion: "REQ-V3-SE-07", type: negative}
  - {name: "test_r6s_age_gate_campus_vs_competitive", criterion: "REQ-V3-SE-08", type: negative}
  - {name: "test_three_tier_scene_matrix", criterion: "REQ-V3-SE-09", type: negative}
  - {name: "test_corpus_text_injection_blocked", criterion: "REQ-V3-SE-10", type: negative}
  # V2 接入（定价 → 出价 → 结算）
  - {name: "test_bid_is_five_percent_of_price", criterion: "REQ-V3-SE-16", type: "unit"}
  - {name: "test_free_game_bids_one_cent", criterion: "REQ-V3-SE-16", type: negative}
  - {name: "test_budget_equals_twenty_impressions", criterion: "REQ-V3-SE-16", type: "unit"}
  - {name: "test_twenty_impressions_exhaust_budget", criterion: "REQ-V3-SE-17", type: deterministic_replay}
  - {name: "test_five_percent_constant_single_source", criterion: "REQ-V3-SE-17", type: negative}
  # 回归与治理
  - {name: "test_full_suite_zero_regression", criterion: "REQ-V3-SE-11", type: deterministic_replay}
  - {name: "test_v3_eval_partition", criterion: "REQ-V3-SE-12", type: deterministic_replay}
```

**硬性约束**：不用 `tmp_path`；每条不变量必须有"破坏后必红"的反例，并接入 `mutation_check.py`。

---

## ⑤ Implementation Steps（开发分步计划）

### 总览

| 阶段 | 目标 | 人的动作 | 估时 | 出口条件 |
|---|---|---|---|---|
| **PR-0** 治理前置 | 解锁所有受保护路径 | 批准 ADR-006、登记 TA-0005 | 1 天（含等人） | 注册表 58 条校验通过 + ADR Accepted |
| **PR-1** 语料接入 | 真实语料能进管道 | 无 | 2.5 天 | 5,000 条投影过 AdRepository + `--corpus` 端到端出 `ad` + 零回归 |
| **PR-2** 合规扩展 | 合规能看见内容分级 | 评审合规改动（safety-critical） | 3 天 | 5×3 场景矩阵 100% 符合 + 五步顺序不变 |
| **PR-3** V2 接入 | 定价 → 出价 → 结算跑通 | 无 | 2 天 | 20 次耗尽对每条样本成立 + `bidding/` 零改动 |
| **PR-4** 评估与收尾 | 证据齐、可交付 | 无 | 1.5 天 | 全量检查绿 + 评估分区报告 |
| | | | **≈10 人天** | |

### 依赖关系（哪些能并行）

```
PR-0 ──▶ PR-1 ──▶ PR-2 ──▶ PR-3 ──▶ PR-4
          │
          └─ 内部可并行：models+repository ｜ select+config

硬卡点：
  · PR-0 的 ADR-006 未 Accepted → 后续全部不能开（check_safety_paths 会拦）
  · TA-0005 必须先于 PR-1 的测试存在（门禁 1）
  · PR-2 与 PR-3 不能并行：都依赖 compliance 的 facts 形参
```

---

### PR-0 · 治理前置（**先于任何代码**，需人工批准）

| # | 动作 | 产出 | 自验 |
|---|---|---|---|
| 0.1 | 写 ADR-006：沿用 `docs/` 的理由、只读语料、投影旁路、合规只动 2 个函数、`scope.out` 的 RAG 条改判 | `docs/architecture/adr-006-v3-corpus-boundary.md` | `check_safety_paths.py --show-paths` 能解析到新清单 |
| 0.2 | 注册表追加 **20 条**（`version: "V3"`，ID 续 ADS 编号）+ `evolution_rounds` 加 V3 + 改 `scope.out` | `docs/req/requirements.yaml` | `validate_requirements.py` PASS，条数 41 → 58 |
| 0.3 | 不变量登记 `INV-V3-001..008` | `docs/architecture/invariants.md` | `validate_requirements.py` 的双向一致性不掉 |
| 0.4 | 覆盖表登记 20 条的测试去向 | `acceptance-coverage-map.yaml` | `fitness_functions.py` PASS |
| 0.5 | 登记 `TA-0005`（具名人类、`approved_at` 早于 PR-1 首次提交） | `docs/test-approvals.yaml` | `check_test_approval.py --base origin/main` 通过 |
| 0.6 | 提交 PR-0 并请求人工批准 ADR | — | PR 上 Gate 1/4/6 全绿 |

> **PR-0 的出口**：注册表 58 条校验通过；ADR-006 状态 `Accepted`（**具名人类**）；`TA-0005` 已登记。
> **没到位就不开 PR-1** —— 否则 PR-1 一提交就会被 `check_safety_paths` 和三道 PR 门禁同时拦住。

---

### PR-1 · 语料接入（不碰冻结层）

| # | 动作 | 产出 | 自验 |
|---|---|---|---|
| 1.1 | `models.py`：`CorpusItem`，**不持有** `description_clean` | `src/corpus/models.py` | 结构断言测试 |
| 1.2 | `repository.py`：只读加载两文件、fail-closed（`CorpusLoadError`） | `src/corpus/repository.py` | 缺文件/坏 JSON/空表三条负例 |
| 1.3 | `projection.py`：`corpus_to_ad` → `(Ad, CorpusFacts)`；`ad_id = ad_<item_id>`；三级兜底 | `src/corpus/projection.py` | 30/30 过 `AD_SCHEMA`（spike 已验证可过） |
| 1.4 | `select.py`：确定性 top-K（命中数降序 + `item_id` 升序） | `src/corpus/select.py` | 双跑 diff = 0；空匹配返回 `[]` |
| 1.5 | `config.yaml` 加 `corpus` 段（路径、K=30、场景标签映射） | `config.yaml` | 配置校验拒绝 K > 50 |
| 1.6 | `fitness_functions.py` 的 `ELEMENT_BY_PACKAGE` 加 `"corpus"` | 同上 | `fitness_functions.py` PASS（**受保护路径，PR-0 的 ADR 覆盖**） |
| 1.7 | 测试 + 变异 + 全量回归 | `test/offline/test_corpus*.py` | 617 → 新增后全绿 |

> **PR-1 的出口**：5,000 条投影全过 `AdRepository`；`python -m app --corpus` 端到端产出 `ad`（≤500 ms）；零回归。

---

### PR-2 · 合规扩展（唯一动冻结层的 PR）

| # | 动作 | 产出 | 自验 |
|---|---|---|---|
| 2.1 | `data/scene-content-rules.yaml`：三档禁项 + 年龄上限 | 新数据文件 | 加载 fail-closed；三档可解析 |
| 2.2 | `run_compliance(..., facts=None)` + `check_scene(..., facts=None)` | `src/compliance/pipeline.py` | 不传 facts 时**行为与 V1 完全一致**（旧测试全绿） |
| 2.3 | 并集判据：`warnings ∪ 映射后的 descriptors` 与场景禁项求交 | 同上 | CS2 在 family 被拒；Among Us 被 warnings 一侧拦下 |
| 2.4 | 年龄兜底：`required_age > 场景上限` → 拒 | 同上 | R6S 在 campus 拒、competitive 过 |
| 2.5 | 五步顺序契约测试 | `test_v3_compliance_order.py` | 步骤列表与 V1 逐位一致 |
| 2.6 | 5×3 矩阵测试（CS2 / Among Us / R6S / Viscera / Stardew × 三档） | `test_v3_compliance_matrix.py` | 15 格全部符合预期 |
| 2.7 | 变异验证：三条新不变量各注入违规 | `scripts/mutation_check.py` | 三条全部可检出 |

> **PR-2 的出口**：矩阵 100% 符合；`mutation_check` 新增 3 条可检出；旧 617 测试零回归。

---

### PR-3 · V2 接入（定价 → 出价 → 结算）

| # | 动作 | 产出 | 自验 |
|---|---|---|---|
| 3.1 | `pricing.py`：`bid_cents_from_price` / `budget_cents_for`（5% 与 20 只在此） | `src/corpus/pricing.py` | `ad_413150`→75、`ad_730`→1、`ad_1086940`→300 |
| 3.2 | `build_bids_v3.py`：生成 sidecar（幂等、逐字节一致） | `scripts/build_bids_v3.py` + `data/bids-corpus.json` | 重跑两次 hash 相同 |
| 3.3 | `pipeline_v2` 透传 `facts` | `src/app/pipeline_v2.py` | `git diff --stat src/bidding/` 为空 |
| 3.4 | `config-v3.yaml`：语料路径、bids sidecar、`logs/bidding-v3.sqlite3` | `config-v3.yaml` | 启动期配置校验 |
| 3.5 | 20 次耗尽测试（免费 / 中价 / 高价三条） | `test_v3_pricing.py` | 20 次后 `exhausted`；第 21 次 `InsufficientBudget` |

> **PR-3 的出口**：V2 端到端在语料上跑通；`bidding/` 零改动（git diff 为证）；20 次耗尽对每条样本成立。

---

### PR-4 · 评估与收尾

| # | 动作 | 产出 | 自验 |
|---|---|---|---|
| 4.1 | V3 评估分区（12–15 条，含 ≥3 条无匹配负例） | `eval/eval_cases.json` | 新分区 `case_count` 登记；负例不硬凑 |
| 4.2 | runner 支持分区统计 | `eval/eval_runner.py` | 旧分区报告与 V2 基线 diff = 0 |
| 4.3 | 同步 `trace-matrix` / `ai-use-log` / 覆盖表 | 三份工件 | `check_ai_use_log.py` 通过 |
| 4.4 | 全量检查（一次跑完） | 见下方命令块 | 全绿 |

```bash
# PR-4 收尾自检（仓库根目录）
python scripts/validate_requirements.py
python scripts/fitness_functions.py
python scripts/check_dependencies.py
python scripts/check_repo_completeness.py
python scripts/check_safety_paths.py --base origin/main
pytest test/offline -q
python scripts/audit_implementation.py
python scripts/mutation_check.py
python eval/eval_runner.py
```

---

### 每周/每 PR 的固定自检（不要等到最后）

```bash
pytest test/offline -q -p no:cacheprovider     # 约 20 秒
python scripts/fitness_functions.py            # S1/S2 会立刻抓到架构漂移
python scripts/validate_requirements.py        # 抓工件不一致
```

> 经验值：本仓库全量 617 测试 ≈ 19 秒、变异验证 ≈ 50 秒。
> **红得越早越便宜**——V2 的教训是治理问题拖到最后才发现（`TD-023`）。

---

### 完成定义（DoD）

- [ ] 20 条 V3 需求全部 `implemented` 或 `verified`，覆盖表无悬空项
- [ ] 8 条 `INV-V3-*` 各有**会失败**的反例，且被 `mutation_check` 检出
- [ ] 旧 617 测试零回归；V3 新增测试全部引用 REQ/INV ID
- [ ] `bidding/`、`ads/`、`scene/`、`selector/` 零改动（git diff 可证）
- [ ] 合规五步顺序与 V1 逐位一致
- [ ] V2 在语料上端到端跑通，20 次耗尽对每条样本成立
- [ ] ADR-006 为 `Accepted`（具名人类），`TA-0005` 在案
- [ ] 评估 V3 分区通过阈值，负例不硬凑
- [ ] `trace-matrix` / `acceptance-coverage-map` / `ai-use-log` 三份工件同步

---

## 回退与未知

- **回退**：PR-1 只新增文件，删除 `src/corpus/` 即回到 V2 状态；PR-2 的合规改动保留 `facts=None` 的旧行为，回退只需不传参；PR-3 回退 = 删 `data/bids-corpus.json` + 去掉 `pipeline_v2` 的 `facts` 实参（竞价逻辑本来就没改）。
- **数据**：全量 25,899 条已在手，入库 5,000 条子集（`data/corpus/`，5.5 MB）；重新抽样只需重跑 `scripts/build_corpus_subset.py`。若语料 `parser_ver` 升版，需重跑 PR-1 验收并更新 manifest。
- **风险**：`data/scene-content-rules.yaml` 一旦入库即为 safety-critical，任何调参都要 ADR + 回归。
- **风险（V2 接入）**：`Ledger.seed()` 会拒绝**已存在账本**中不同的报价契约 —— 改了 5% 口径或语料集合后，
  旧的 `logs/bidding-v2.sqlite3` 必须换路径或删除，否则报 `persistent seed contract cannot be changed`。
  demo 用 `logs/bidding-v3.sqlite3` 隔离。

---

## 人工批准记录

| 项 | 内容 |
|---|---|
| 计划文件 | `docs/plans/V3-execution.md` |
| 提交评审时间 | 2026-11-17 |
| **批准者（具名人类）** | ⏳ 待填 |
| 批准时间 | ⏳ |
| 批准结论 | ⏳ `APPROVED` / `CHANGES REQUIRED` / `REJECTED` |

> **No agent may self-approve**（课程 §11.3）。
