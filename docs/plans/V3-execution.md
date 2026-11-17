# V3 执行计划（Execution Plan）· 真实语料接入

> **状态**：草案待人工批准（批准前禁止写代码）
> **依据**：`docs/req/requirements-v3-se.md`（15 条需求）、`V3spike结论.md`（可行性实测）、
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
invariants:
  - "INV-ADS-001（compliance 不可绕过）—— 必须保持"
  - "INV-V3-001 语料不进 Ad 契约（新增）"
  - "INV-V3-002 候选生成确定性且无状态（新增）"
  - "INV-V3-003 内容并集判据必拦截（新增）"
  - "INV-V3-004 年龄兜底必拦截（新增）"
  - "INV-V3-005 权威链顺序不变（新增）"
  - "INV-V3-006 语料文本不可信（新增）"
test_design: "pytest 离线确定性（MockLLM）+ 真实 30 条样本作为只读夹具；无网络、无临时目录"
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
target_files_pr3: ["scripts/fitness_functions.py", "docs/architecture/*.md",
                   "docs/req/requirements.yaml", "eval/*", "docs/ai-use-log.yaml"]
target_files_pr0: ["docs/req/requirements.yaml", "docs/architecture/adr-006-*.md",
                   "docs/architecture/invariants.md", "docs/code-governance/acceptance-coverage-map.yaml"]
allowed_imports: ["json", "pathlib", "dataclasses", "typing", "collections.abc", "yaml"]
prohibited_imports: ["requests", "urllib", "random", "time", "audit", "selector", "compliance"]
data_access: "只读 demo_steam_30 派生的仓库内子集；audit 只写不读"
frozen_paths_not_touched: ["src/ads/", "src/scene/", "src/selector/", "src/bidding/"]
```

**触及的受保护路径**（`check_safety_paths.py --show-paths`）：
`src/compliance/`、`data/`、`eval/`、`scripts/fitness_functions.py`、`docs/req/requirements.yaml`、
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
  # 回归与治理
  - {name: "test_full_suite_zero_regression", criterion: "REQ-V3-SE-11", type: deterministic_replay}
  - {name: "test_v3_eval_partition", criterion: "REQ-V3-SE-12", type: deterministic_replay}
```

**硬性约束**：不用 `tmp_path`；每条不变量必须有"破坏后必红"的反例，并接入 `mutation_check.py`。

---

## ⑤ Implementation Steps

### PR-0 · 治理前置（**先于任何代码**，需人工批准）

1. 写 `docs/architecture/adr-006-v3-corpus-boundary.md`：
   - 为什么沿用 `docs/`（验证平面绑定路径，新建 `docs3/` 会让 V3 脱离自动化校验）；
   - 只读语料、投影旁路、不扩 AD_SCHEMA；
   - 合规只动 2 个函数、五步顺序不变；
   - `scope.out` 的 RAG 条从"延后到 V3"改为"V4 或 withdrawn"。
2. `docs/req/requirements.yaml`：追加 15 条（`version: "V3"`）+ `evolution_rounds` 加 V3 + 改 `scope.out`。
3. `docs/architecture/invariants.md`：追加 `INV-V3-001..006`（**仅只读，须人工批准**）。
4. `docs/code-governance/acceptance-coverage-map.yaml`：登记 15 条的测试去向。
5. `docs/test-approvals.yaml`：新增 `TA-0005`，覆盖 PR-1 的语料测试（**具名人类、时间早于实现**）。
6. 跑 `validate_requirements.py` + `check_safety_paths.py --base origin/main`，确认 ADR 伴随通过。

> **PR-0 的验收**：注册表 56 条（41+15）校验通过；ADR-006 状态为 Accepted；TA-0005 已登记。

### PR-1 · 语料接入（不碰合规）

7. `src/corpus/models.py` + `repository.py`：只加载轻字段，`CorpusLoadError` fail-closed。
8. `src/corpus/projection.py`：`corpus_to_ad` 返回 `(Ad, CorpusFacts)`；`ad_id = ad_<item_id>`；三级兜底。
9. `src/corpus/select.py`：确定性 top-K（K 来自 config）。
10. `config.yaml` 加 `corpus` 段；`scripts/fitness_functions.py` 的 `ELEMENT_BY_PACKAGE` 加 `"corpus"`。
11. 测试 + 变异；跑全量回归（617 应为 617+ 新增）。

> **PR-1 的验收**：30 条投影全部通过 `AdRepository`；管道能端到端产出 `ad`；零回归。

### PR-2 · 合规扩展（唯一动冻结层的 PR）

12. `data/scene-content-rules.yaml`：三档禁项 + 年龄上限。
13. `src/compliance/pipeline.py`：`run_compliance(..., facts=None)`、`check_scene(..., facts=None)`；并集判据 + 年龄兜底。
14. 反例测试：CS2 / Among Us / R6S / Viscera / Stardew 五条真实样本 × 三个场景矩阵。
15. 管道顺序契约测试（证明五步没动）。

> **PR-2 的验收**：三档矩阵 100% 符合预期；`mutation_check` 新增不变量全部可检出。

### PR-3 · 评估与收尾

16. `eval/eval_cases.json` 加 V3 分区（12–15 条，含 ≥3 条无匹配负例）；`eval_runner.py` 支持分区统计。
17. 同步 `trace-matrix` / `ai-use-log` / `acceptance-coverage-map`。
18. 全量检查：需求 schema、fitness、依赖、完整性、安全路径、评估 replay、变异验证。

---

## 回退与未知

- **回退**：PR-1 只新增文件，删除 `src/corpus/` 即回到 V2 状态；PR-2 的合规改动保留 `facts=None` 的旧行为，回退只需不传参。
- **未知**：全量 25,899 条语料尚未交付，本计划只用 30 条样本 + 仓库内子集（建议 300 条）；若语料形态变化，`parser_ver` 升版需重跑 PR-1 的验收。
- **风险**：`data/scene-content-rules.yaml` 一旦入库即为 safety-critical，任何调参都要 ADR + 回归。

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
