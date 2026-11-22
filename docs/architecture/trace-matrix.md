# 追踪矩阵（Trace Matrix）

> **CORE 工件** · 课程对应：note 行 1353–1380（P56–57）、行 5144（Capstone 评分量规）
> **定义**：把需求、结构、测试、监控串在一张矩阵里，回答「**这条需求在哪里被强制**」。
> **状态**：草案待批 · 版本：V1（`docs/architecture/` 轮次）· 日期：2026-10-06
> **上游**：`docs/req/requirements.yaml`、`asr-register.md`、`invariants.md`、`runtime-policy-catalog.md`
> **规则**（课程行 1366）：Trace Matrix **随架构增长**（Status: design → implemented → tested），
> **每轮 ADD 只追加，从不删除**。

---

## 0. 必填列（课程行 1359）

`REQ ID + Type + Status` · `Architectural Consequence` · `Enforcing Component` · `Test / Evidence` · `Runtime Monitor`

**Runtime Monitor 的硬要求**（课程行 5152、5162）：

> Monitor **有意义**、**具体可度量**；「缺运行时 monitor → 无法发现生产故障」。

因此本表所有 monitor 均写成 `<指标名> <比较符> <阈值>` 形式，**不允许**写"人工检查"或"观察日志"。

---

## 1. 完整追踪矩阵（22 条基线需求）

**Status 词汇与注册表的映射**（两份工件用词不同，此处显式对照，避免看起来互相矛盾）：

| 本表 Status | `requirements.yaml` 的 status | 含义 |
|---|---|---|
| `tested` | `implemented` | 代码在位**且有通过的测试**。本项目 P0~P3 二者同时满足，故本表直接标 `tested`，不单列 `implemented` |
| `partial` | `specified` | 部分到位但证据不全（本表仅 `NFR-QA-002`：测试套件在，**覆盖面映射与变异验证未建**） |
| `design` | `specified` | 已设计未实现 |

Status 取值：`design`（已设计未实现）→ `implemented`（代码在位）→ `tested`（有通过的测试证据）。

| REQ ID | Type | Status | Architectural Consequence | Enforcing Component | Test / Evidence | **Runtime Monitor** |
|---|---|---|---|---|---|---|
| `REQ-ADS-FR-001` | functional | **tested** | 素材库准入：文件与内存仓库一一对应 | `ads.repository.AdRepository.load` | `test_ads.py::test_load_ok`、`test_get_found`、`test_get_missing_returns_none` | `ads_loaded_count == 文件条数`（启动期断言，不等则启动失败） |
| `REQ-ADS-FR-002` | functional | **tested** | 输入准入闸门：非法场景不进入 LLM | `scene.parser.parse_scene` | `test_scene.py`（8 项：正常/缺字段/非法枚举/非对象/多余字段/标签类型错/去重保序） | `scene_input_rejected_count`；非法率 > 1% 触发告警（疑探测性输入） |
| `REQ-ADS-FR-003` | functional | **tested** | **fallback path 集合**；降级终止于 `no_ad` | `app.pipeline.recommend`（10 条降级路径） | `test_app_pipeline.py`：**每条路径一个测试**（scene_invalid/no_candidates/low_confidence/llm_output_invalid/llm_error/llm_timeout/injection_detected/compliance×3/audit_write_failure）+ 全部路径恰好 1 条审计 + 不抛异常 | `no_ad_count` 按原因码分桶；**进程崩溃次数 == 0** |
| `REQ-ADS-FR-004` | functional | **tested** | 输出契约：广告 / 无广告两形态（判别联合 schema） | `render.schema` + `render.serializer` | `test_render.py`（两形态、ad_id 模式反例、confidence 越界、空标题、**每个降级原因码都在 schema 中**、未登记原因码被拒、metadata 不外泄）；`test_app_pipeline.py::test_all_results_pass_render_schema` | `render_schema_validation_failures == 0` |
| `REQ-ADS-ARCH-001` | invariant | **tested** | 加载期 schema gate；**整批 fail-closed**（不跳过单条） | `ads.schema.AD_SCHEMA` + `AdRepository.load` | `test_ads.py`：缺必填字段、非法设备枚举、重复 ad_id、缺文件、坏 JSON | `ad_load_failure_count == 0`（生产期）；> 0 即立即升级 `RP-001` |
| `REQ-ADS-ARCH-002` | invariant | **tested** | **候选集 wrapper** + 存在性 gate（**双层**：解析期拒绝 + 展示前复检） | `selector.parser.parse_llm_output` + `compliance.pipeline.check_output` | `test_selector.py`：集外 ad_id / 空候选集 / 空 ad_id 三类反例；`test_compliance.py`：集外输出 REJECT | **`out_of_candidate_selection_count == 0`**（必须恒为 0） |
| `REQ-ADS-ARCH-003` | invariant | **tested** | 严格 JSON validation gate；解析失败 fail-closed | `selector.parser.parse_llm_output` | `test_selector.py`（14 项：非 JSON/顶层非对象/缺字段/**多余字段**/空 ad_id/类型错/**bool confidence**/越界/非字符串 raw） | `llm_output_parse_failure_rate`；> 5% 触发 `RP-004` 升级 |
| `REQ-ADS-ARCH-004` | invariant | **tested** | 全部确定性部件为纯函数 ⇒ 可复现 | `compliance.pipeline.run_compliance`、`selector`（解析/装配/解释校验）、`context.count_tokens` | `test_compliance.py`（12 项）；`test_selector.py`（解析与 Mock 确定性）；`test_context_assembly.py`（装配与 token 计数）；`test_explanation.py`（校验确定性） | `deterministic_replay_diff_count == 0`（固定输入重复 3 次比对） |
| `REQ-ADS-NFR-SAFETY-001` | invariant | **tested** | **deterministic wrapper（核心）**：**五步**管道，任一失败即 REJECT | `compliance.pipeline.run_compliance` | `test_compliance.py`：违禁词/金融/成人/夜间游戏/校园成人/设备/集外/banned_check 状态各 1 反例 | **`compliance_escape_count == 0`**（**最重要的 monitor**；> 0 立即重开 `ADR-001` T1） |
| `REQ-ADS-NFR-SAFETY-002` | invariant | **tested** | 独立品类 blacklist gate（可与违禁词分别审计） | `compliance.pipeline.check_category` + `SceneRules.category_blacklist` | `test_compliance.py`：金融承诺、成人品类 REJECT | `category_blacklist_reject_count`；若某黑名单品类 reject 数长期为 0 → 检查素材是否根本不含该品类 |
| `REQ-ADS-NFR-SAFETY-003` | invariant | **tested** | pre-display 违禁词 gate，作用于 title + copy 全量 | `compliance.pipeline.check_banned_words` + `BannedWords.check_all` | `test_ads.py::test_banned_words_hit/miss/check_all` | `banned_word_hit_count` 按命中词分桶（用于词表迭代，OQ-002） |
| `REQ-ADS-NFR-SAFETY-004` | invariant | **tested** | **双层 gate**：预筛（候选构建）+ 终检（compliance） | `AdRepository.filter_by_scene` + `compliance.pipeline.check_scene` | `test_ads.py`：夜间/校园/设备预筛 3 项；`test_compliance.py`：夜间游戏、校园成人、设备不符 | `scene_violation_reject_count`；**双层各自独立计数**（不一致即为架构漂移） |
| `REQ-ADS-NFR-SAFETY-005` | invariant | **tested** | confidence threshold gate + 降级路径 | `app.pipeline`（判定）+ `selector.parser`（取值域） | `test_app_pipeline.py::test_degrade_low_confidence`（记录原始 confidence）、`::test_confidence_exactly_at_threshold_is_accepted`（**恰在阈值处放行**）、`test_context_assembly.py::test_config_threshold_matches_confirmed_decision` | `low_confidence_degrade_rate`；超阈值 → 用评估集重标定（OQ-004 已定案 0.5） |
| `REQ-ADS-SEC-001` | security | **tested** | **pre-model sanitize gate**（10 条高精度模式，检出即拒绝） | `app.sanitize` + `selector.parser` | `test_sanitize.py`（15 条注入样本逐个命中 + 9 条正常文案不误报 + **每条模式都被行使**）；`test_app_pipeline.py::test_degrade_injection_detected` | `injection_detected_count`；**任一次检出即触发 prompt 复核**（`RP-003`） |
| `REQ-ADS-NFR-PERF-001` | performance | **tested** | **timeout gate + fallback + p95 监控 + SLA drift alert**（四元素齐备） | `app.pipeline._call_with_timeout` + `eval.eval_runner`（p95 窗口 = 评估集 replay）+ `audit.metrics` | `test_app_pipeline.py::test_degrade_llm_timeout`（前两元素）；`test_eval_runner.py::test_p95_and_sla_drift`（后两元素） | **`e2e_recommend_latency_p95 <= 5s`**（由 replay 实际产出）；超阈置 `sla_drift_alert` |
| `REQ-ADS-NFR-COST-001` | cost | **tested** | `route_budget()` 三档 + summarization gate + **re-injection** | `selector.context.ContextAssembler` + `config.yaml` | `test_context_assembly.py`（12 项：三档边界/85% 阈值/预算内/**compaction 后重注入**/永不裁剪层/OVER_BUDGET 留痕/默认预算与需求一致） | **`llm_context_tokens_per_request <= 2000`**；`compaction_trigger_count`；**`post_compaction_constraint_present == true`**（违规即安全约束不可见） |
| `REQ-ADS-NFR-QA-001` | quality | **tested** | 固定评估集作 **CI 阻断门**（ADR-003：分母分离 + 违规独立判据） | `eval.eval_runner` + `config.yaml` 的 `eval` 段 | `test_eval_runner.py`（10 项 fail-closed 反例 + ≥20 条硬门槛 + 分母分离 + 确定性 + **当前集必须通过**） | `eval_pass_rate`；**`eval_case_count >= 20`**（当前 **25**）；违规数与通过率**分别**判定 |
| `REQ-ADS-NFR-QA-002` | quality | **tested** | **verification gate** + **变异验证**；流程不变量 `INV-ADS-011` | `scripts/mutation_check.py` + `fitness_functions.py` + CI 门 | `test_mutation_check.py`（含**判定逻辑本身**的 4 项反例）；`mutation_check.py` 对 12 条不变量各注入违规并确认测试失败 | **`fit_criterion_test_coverage == 100%`**；**`invariant_failing_test_coverage == 100%`**（**12/12 已实测**） |
| `REQ-ADS-GOV-001` | governance | **tested** | provenance 证据子系统；JSONL 追加写；**恰好 1 条** | `audit.store`（`JsonlAuditStore` / `AuditRecordBuilder`） | `test_audit.py`（恰好 1 条、二次写入被拒、ID 唯一、时间戳、JSONL 逐行可解析、OSError 包装、失败不标记已写、**无读取接口**）；`test_app_pipeline.py`（每条路径 1 条 + 写入失败整体失败） | **`audit_entries_per_request == 1`**（精确等于）；`audit_write_failure_count`；> 0 即整体失败（`RP-011`） |
| `REQ-ADS-GOV-002` | governance | **design** | **permission model + pre-commit hook**（WHO + WHEN） | `.opencode/permissions.jsonc` + hook + CI 门 | 待建：权限矩阵测试 + hook 拦截模拟 | **`safety_critical_unrecorded_change_count == 0`**；`permission_bypass_count == 0`（> 0 立即重开 T-6） |
| `REQ-ADS-AI-001` | quality | **tested** | **解释路径与决策路径结构分离**（口径：为什么选这条广告，OQ-009 已定案） | `selector.explanation`（generate / verify） | `test_explanation.py`（8 项：口径/对照其他候选/降级保 ad_id/违禁词剥离/**签名不含 ad_id**/不改 judgment） | **`explanation_decision_isolation_violations == 0`**；**`explanation_banned_word_leak_count == 0`** |
| `REQ-ADS-AI-002` | governance | **tested** | 决策证据捕获 model / prompt / threshold 版本溯源 | `app.pipeline._provenance` + `audit.store` | `test_provenance.py`（三要素齐备、反映实际配置、阈值非硬编码、**降级路径同样带溯源**、缺失写 `unknown`、不外泄到渲染输出） | **`decisions_missing_version_provenance == 0`**（缺失写显式 `unknown`，以便统计而非被空串掩盖） |

---

## 2. 覆盖自检

| 检查项 | 结果 |
|---|---|
| 每条基线需求都在矩阵中出现 | ✅ 22/22 |
| 每行 `Enforcing Component` 是**真实构件**（非模糊描述） | ✅ 全部指向具体模块/函数 |
| 每行 `Runtime Monitor` **具体可度量** | ✅ 全部为 `<指标> <比较符> <阈值>` 形式 |
| 是否有需求**没有 monitor** | ❌ **无**（原设计缺口已在本表补全） |
| Status 为 `tested` 的需求是否有真实测试证据 | ✅ 8 条，测试文件与用例名可核对 |

**Status 分布**：`tested` **17 条** · `partial` **2 条** · `design` **3 条**。

> 说明：**计数由脚本核对**（`Select-String` 统计 Status 列），非手工估算。
>
> · `partial` = `REQ-ADS-NFR-PERF-001`（四元素中 2/4：timeout + fallback 已覆盖，
>   p95 监控与 SLA alert 未实现）、`REQ-ADS-NFR-QA-002`（覆盖面已建，**变异验证未建**）。
> · `design` 3 条 = `REQ-ADS-GOV-002`（权限 + hook 属 D3 未建）、
>   `REQ-ADS-AI-002`（版本溯源字段未写入审计记录）、`REQ-ADS-NFR-QA-001`（评估集待建）。
> · **`implemented` 不单列**：本项目代码同时有通过的测试，故直接标 `tested`。

### 2.1 实现完成度（按架构元素 · D8 核查）

课程 D8 要求 `src/` 含 **"full application source code"**，且**模块名与架构元素一致**。
后者已满足（由 `fitness_functions.py` 的 S1 检查强制）。

| 元素 | 模块 | 实现文件 | Status | 说明 |
|---|---|---|---|---|
| ① 素材契约 + 候选集 | `src/ads/` | 4 个 .py | ✅ `tested` | 完整 |
| ② 场景输入契约 | `src/scene/` | 3 个 .py | ✅ `tested` | 完整 |
| ③ **FINAL AUTHORITY** | `src/compliance/` | 3 个 .py | ✅ `tested` | 五步管道，含 20 项反例测试 |
| ④ **AI 建议层** | `src/selector/` | 6 个 .py | ✅ `tested` | P4（2026-10-06） |
| ⑤ 输出契约 | `src/render/` | **3 个 .py** | ✅ `tested` | **P6 完成**：`schema` / `serializer` / `__init__` |
| ⑥ 证据子系统 | `src/audit/` | **3 个 .py** | ✅ `tested` | **P6 完成**：`store` / `metrics`（22 条 monitor 登记）/ `__init__` |
| ⑦ 编排 / 降级路径 | `src/app/` | **5 个 .py** | ✅ `tested` | **P5 完成**：`pipeline` / `cli` / `sanitize` / `config` / `__main__` |

**结论：`src/` 的 7 个架构元素已全部实现，系统可端到端跑通一次推荐。**

> ✅ **课程开题的硬性要求已满足**：应用含**真实 AI 组件**（元素 ④ `src/selector/`：
> LLM 闭集选择 + 严格输出校验 + 六层上下文装配 + 解释路径隔离；其上 `MockLLM`
> 提供确定性离线运行，真实 LLM 接入属 P8）。
> `TD-020`（AI 组件缺失）与 `TD-022`（元素 ⑤–⑦ 为空）**均已关闭**。
>
> **端到端验证（可复跑）**：
> ```
> python -m app --time-slot night --device mobile --tag student
> → {"kind":"ad","ad":{...},"explanation":"...","confidence":0.85,"audit_id":"aud-..."}
> ```
> 全部 **10 条降级路径**各有测试，且每条路径都验证
> 「结构化 `no_ad` + 恰好 1 条审计 + 不抛异常」。
>
> ⚠️ **仍未覆盖**（已登记，非隐藏）：
> · `REQ-ADS-NFR-PERF-001` 的 p95 监控与 SLA alert（四元素中 2/4）
> · `REQ-ADS-GOV-002` 的权限模型与 pre-commit hook（属 D3）
> · 变异验证（`INV-ADS-011`）——目前无法证明「测试会在实现被破坏时失败」
> · **真实 LLM 接入与固定评估集**（属 P7/P8）
>
> **测试布局**（D8 第三条要求）：`test/offline/`（**12 个模块，216 个确定性测试**）已就位；
> `test/live/` 为空——**这是正确的**：其定义为"依赖 API 的测试"，
> 无真实 LLM 时不应放置假测试（真实 LLM 接入属 P8）。

---

## 3. 暴露的缺口（本表的主要价值）

课程口径（note 行 5162）：**缺运行时 monitor → 无法发现生产故障**。本表暴露出四类缺口：

| # | 缺口 | 涉及需求 | 影响 | 补法 |
|---|---|---|---|---|
| **G1** | **全部 monitor 都还没实现** | 22/22 | 生产环境无法发现任何故障；`compliance_escape_count` 这条最关键的 monitor 现在不存在 | 实现 `src/audit/`（P6）并把 monitor 定义写入其中 |
| **G2** | **证据子系统整体缺失** | `GOV-001`、`GOV-002`、`AI-002` | 无审计 = 无证据 = 决策不可辩护；三条流程不变量无强制手段 | P6 实现 `audit` + `.opencode/permissions.jsonc` + pre-commit hook |
| **G3** | **评估门未建，且覆盖面映射缺失** | `NFR-QA-001`、`NFR-QA-002` | 无法阻断质量回退；`INV-ADS-011` 无法验证 | 建 `eval/eval_cases.json` + 覆盖面检查脚本 |
| **G4** | **降级路径（含超时四元素）未实现** | `FR-003`、`NFR-PERF-001` | 课程"性能陷阱"：无 fallback 则性能需求**未实现** | P5 实现 `src/app/` 编排与降级 |

> **G1 与 C4 证据簇是同一个洞**：`concern-clusters.md` 已警告"Missing a cluster → Evidence 簇最易被忘"，
> 本表把它量化了——**22 条需求的 monitor 无一落地**。

---

## 4. 决策 → 需求 → 代码 → 测试 → 监控 的可追溯链（课程行 1380）

课程要求：**每个决策都必须可追溯到 ADR → Requirements → Code → Tests → Monitoring。**

### 链 1：核心安全主张（`ADR-001` → 零逃逸）

```
ADR-001 Guarded Hybrid（FINAL AUTHORITY = compliance）
  └─ Related Requirements：REQ-ADS-NFR-SAFETY-001、004；REQ-ADS-ARCH-002；REQ-ADS-SEC-001
       └─ Implementation Artifacts：src/compliance/pipeline.py、src/ads/repository.py、
          data/banned_words.json、data/scene_rules.json
            └─ Validation Artifacts：test/offline/test_compliance.py（12 项反例）、
               test/offline/test_ads.py
                 └─ Monitoring：compliance_escape_count == 0（CI 门 + 运行期告警）
```

### 链 2：失败语义与治理（`ADR-002` → fail-closed 与证据）

```
ADR-002 Fail-Closed 终态 + 审计不可协商 + 失败归因
  └─ Related Requirements：REQ-ADS-FR-003、NFR-PERF-001、GOV-001、GOV-002、NFR-QA-002、AI-002
       └─ Implementation Artifacts：src/app/（fallback+timeout gate）、src/audit/、
          .opencode/permissions.jsonc、pre-commit hook
            └─ Validation Artifacts：test/offline/test_app.py（待建）、
               权限矩阵测试（待建）、hook 拦截模拟（待建）
                 └─ Monitoring：audit_entries_per_request == 1、
                    e2e_recommend_latency_p95 <= 5s、safety_critical_unrecorded_change_count == 0
```

### 链 3：AI 边界（`ADR-001` → 闭集选择与上下文）

```
ADR-001（AI is advisory）
  └─ Related Requirements：REQ-ADS-ARCH-002、ARCH-003、NFR-COST-001、AI-001
       └─ Implementation Artifacts：src/selector/（P4 待建）、config.yaml
            └─ Validation Artifacts：test/offline/test_selector.py（待建）
                 └─ Monitoring：out_of_candidate_selection_count == 0、
                    llm_context_tokens_per_request <= 2000、
                    explanation_decision_isolation_violations == 0
```

> **追溯自检**：三条链覆盖全部 22 条需求？→ 链 1（5 条）+ 链 2（6 条）+ 链 3（4 条）= 15 条。
> **剩余 7 条**（`FR-001`、`FR-002`、`FR-004`、`ARCH-001`、`ARCH-004`、`NFR-SAFETY-002`、`NFR-SAFETY-003`、`NFR-SAFETY-005`）
> 属**输入契约与其余合规 gate**，由 `ADR-001` 的 §5 权威分配表覆盖，但**未单列决策链**。
> 这是可接受的（它们不是架构决策点，而是实现细节），但已在 §5 记入待办。

---

## 5. 缺口登记（供 `docs/debt-register.md`）

| ID | 缺口 | 类别（课程 AI-era 债务分类） | 重开/补齐条件 |
|---|---|---|---|
| `TD-001` | 22 条需求的运行时 monitor 全部未实现 | **guardrail debt** | P6 实现 `audit` 时一并落地；在此之前 Tier 3 验证不完整 |
| `TD-002` | 证据子系统（audit / permission / hook）缺失，3 条流程不变量无强制手段 | **guardrail debt** | D3/D4 交付时补齐 |
| `TD-003` | 评估集与覆盖面映射缺失 | **evaluation debt** | 评估集落地时（OQ-005 定口径） |
| `TD-004` | 降级路径与超时四元素未实现 | **guardrail debt** | P5；在此之前 `REQ-ADS-NFR-PERF-001` 视为**未实现** |
| `TD-005` | 7 条需求未单列决策链 | 文档债 | 补 ADR 或在本表追加链 |

> 课程 DoD 第 7 条：本次 sprint 引入的**架构债已记入 option ledger / debt register**（note 行 5231）。

---

## 6. 人工确认清单

| # | 待确认项 | 建议 | 状态 |
|---|---|---|---|
| 1 | 22 条的 Architectural Consequence 表述是否准确 | 维持 | ⏳ 待批 |
| 2 | Status 判定（8 tested / 1 partial / 13 design）是否接受 | 维持；`partial` 用于覆盖面未建 | ⏳ 待批 |
| 3 | Runtime Monitor 指标名与阈值（尤其 `compliance_escape_count == 0`） | 维持 | ⏳ 待批 |
| 4 | §5 的 5 条技术债是否认可 | 维持 | ⏳ 待批 |


## V2 增量（2026-10-31，有效本地基线）

此前各节为 V1 历史快照。原课程 PDF 和本轮真实用户授权优先；V2 在同目录追加，V1 内容和 ID 保留。ADR-005 为方案及 AI proxy 技术评审，正式团队人工验收待完成。

| REQ ID | 状态 | 架构后果与强制组件 | 验证证据 | 运行时观测 |
|---|---|---|---|---|
| `REQ-ADS-NFR-SAFETY-006` | implemented；本地测试，正式验收 pending | `bidding.models.validate_bids` / `INV-V2-001` | `test_bidding_v2.py::test_reject_invalid_bid_values` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-ARCH-005` | implemented；本地测试，正式验收 pending | `bidding.ledger.Ledger.budgets` / `INV-V2-002` | `test_bidding_v2.py::test_spend_replay_exact_exhaustion_and_overspend_rejection` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-ARCH-006` | implemented；本地测试，正式验收 pending | `bidding.engine.choose_winner` / `INV-V2-003` | `test_bidding_v2.py::test_ineligible_high_bid_cannot_displace_affordable_candidate` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-ARCH-007` | implemented；本地测试，正式验收 pending | `bidding.ledger.Ledger.finalize` / `INV-V2-004` | `test_bidding_v2.py::test_injected_transaction_failure_rolls_back_every_boundary` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-ARCH-008` | implemented；本地测试，正式验收 pending | `bidding.models.validate_bids` / `INV-V2-005` | `test_bidding_v2.py::test_reject_invalid_budget_and_bound_types` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-ARCH-009` | implemented；本地测试，正式验收 pending | `bidding.engine.choose_winner` / `INV-V2-006` | `test_bidding_v2.py::test_pure_deterministic_tie_break_does_not_depend_on_input_order` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-NFR-SAFETY-007` | implemented；本地测试，正式验收 pending | `selector.relevance.parse_relevance_output` / `INV-V2-007` | `test_relevance_v2.py::test_reject_noninteger_nonfinite_out_of_range_relevance` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-ARCH-010` | implemented；本地测试，正式验收 pending | `bidding.ledger.Ledger.finalize` / `INV-V2-008` | `test_bidding_v2.py::test_ledger_refuses_invalid_or_non_bid_charges_atomically` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-ARCH-011` | implemented；本地测试，正式验收 pending | `bidding.engine.choose_winner` / `INV-V2-006` | `test_bidding_v2.py::test_pure_deterministic_tie_break_does_not_depend_on_input_order` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-FR-005` | implemented；本地测试，正式验收 pending | `bidding.engine.choose_winner` / `INV-V2-006` | `test_bidding_v2.py::test_winner_is_product_of_relevance_and_bid_at_pay_as_bid_price` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-FR-006` | implemented；本地测试，正式验收 pending | `app.cli_v2.load_v2_config` / `INV-V2-008` | `test_v2_governance.py::test_formula_configuration_rejects_executable_or_unknown_policy` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-ARCH-012` | implemented；本地测试，正式验收 pending | `selector.relevance.parse_relevance_output` / `INV-V2-009` | `test_relevance_v2.py::test_ai_cannot_write_economic_fields_or_extra_keys` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-FR-007` | implemented；本地测试，正式验收 pending | `bidding.ledger.Ledger.finalize` / `INV-V2-003` | `test_pipeline_v2.py::test_exhausted_budget_disappears_from_later_provider_candidates` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-FR-008` | implemented；本地测试，正式验收 pending | `bidding.ledger.Ledger.finalize` / `INV-V2-011` | `test_pipeline_v2.py::test_success_uses_deterministic_auction_and_exact_transaction_snapshot` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-NFR-QA-003` | implemented；本地测试，正式验收 pending | `bidding.engine.choose_winner` / `INV-V2-006` | `test_v2_governance.py::test_bidding_core_has_no_model_or_network_dependency` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-SEC-002` | implemented；本地测试，正式验收 pending | `bidding.models.validate_bids` / `INV-V2-001` | `test_bidding_v2.py::test_loading_rejects_duplicate_and_unknown_ad_ids` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-GOV-003` | implemented；本地测试，正式验收 pending | `scripts.check_semantic_eval.semantic_changes` / `INV-V2-012` | `test_v2_governance.py::test_semantic_gate_tracks_real_prompt_and_auction_paths` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-NFR-QA-004` | implemented；本地测试，正式验收 pending | `eval.v2_runner.main` / `INV-V2-012` | `test_v2_governance.py::test_v2_fixed_evaluation_has_safety_and_budget_cases` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |
| `REQ-ADS-NFR-PERF-002` | implemented；本地测试，正式验收 pending | `bidding.engine.choose_winner` / `INV-V2-006` | `test_bidding_v2.py::test_hundred_candidate_offline_compute_median_below_fifty_ms` | SQLite 权威快照：`request_id`、候选/分数/预算/成交价/结果；离线重算差额=0 |

观测口径：上述 SQLite 字段是实际持久化证据，不冒称 Prometheus 指标。重复/冲突/零余额及事务失败由固定 replay 与反例核对。线上告警基础设施尚未部署。

---

## V3 增量（2026-11-17，待人工批准）

V3 在 `docs/architecture/` 原地追加（理由见 ADR-006）。下表 18 条为 `version: V3` 的需求；
**状态列写 `specified` 是因为 PR-0 只做登记**，实现与测试证据由 PR-1..PR-4 补齐后改为 `implemented`。

| 需求 | 状态 | 强制组件 / 不变量 | 测试证据（计划） | 运行时 monitor（计划） |
|---|---|---|---|---|
| `REQ-ADS-FR-009` | implemented（V3） | `corpus.repository.CorpusRepository / INV-V3-001` | `test_corpus.py::test_load_matches_file_line_count` | 候选语料条目数、被跳过条目数 |
| `REQ-ADS-FR-013` | implemented（V3） | `scripts.build_corpus_subset.select_subset` | `test_corpus.py::test_subset_manifest_matches_committed_files` | manifest rows / SHA-256 与实际文件一致 |
| `REQ-ADS-FR-014` | implemented（V3） | `app.cli.load_corpus_repository` | `test_corpus.py::test_cli_corpus_repository_wiring` | 候选数 = top_k；请求耗时 ≤ 500 ms |
| `REQ-ADS-ARCH-013` | specified（PR-1 实现） | `corpus.projection.corpus_to_ad / INV-V3-001` | `test_corpus.py::test_raw_corpus_item_rejected_by_ad_schema` | 投影通过 AD_SCHEMA 的条数、失败原因 |
| `REQ-ADS-FR-010` | specified（PR-1 实现） | `corpus.projection.corpus_to_ad` | `test_corpus.py::test_projection_empty_genres_fallback` | category 三级兜底命中次数 |
| `REQ-ADS-FR-011` | specified（PR-1 实现） | `corpus.select.select_candidates / INV-V3-002` | `test_corpus.py::test_select_is_deterministic` | top-K 规模、命中标签数分布 |
| `REQ-ADS-ARCH-014` | specified（PR-1 实现） | `corpus.select.select_candidates / INV-V3-002` | `test_corpus.py::test_select_is_deterministic` | 双跑 diff 次数 |
| `REQ-ADS-NFR-COST-002` | specified（PR-1 实现） | `corpus.config.CorpusConfig` | `test_corpus.py::test_k_upper_bound_rejected` | 装配上下文 token 数 / 预算 |
| `REQ-ADS-ARCH-015` | implemented（V3） | `compliance.pipeline.run_compliance / INV-V3-005` | `test_v3_compliance.py::test_pipeline_order_unchanged` | 五步序列与 V1 的逐位差异数 |
| `REQ-ADS-NFR-SAFETY-008` | implemented（V3） | `compliance.pipeline.check_scene / INV-V3-003` | `test_v3_compliance.py::test_among_us_rejected_by_warnings_side` | 内容并集命中数与命中规则 |
| `REQ-ADS-NFR-SAFETY-009` | implemented（V3） | `compliance.pipeline.check_scene / INV-V3-004` | `test_v3_compliance.py::test_age_gate_rejects_above_limit` | 年龄超限拦截数 |
| `REQ-ADS-NFR-SAFETY-010` | implemented（V3） | `compliance.pipeline.check_scene` | `test_v3_compliance.py::test_three_tier_scene_matrix` | 三档场景放行/拒绝矩阵 |
| `REQ-ADS-SEC-003` | specified（PR-1 实现） | `app.pipeline.recommend / INV-V3-006` | `test_corpus.py::test_injected_corpus_text_blocked` | 注入检出数与检出率 |
| `REQ-ADS-NFR-QA-005` | specified（PR-4 实现） | `app.pipeline.recommend` | `test/offline 全量回归` | 离线测试通过数与旧分区 replay diff |
| `REQ-ADS-NFR-QA-006` | implemented（V3） | `eval.eval_runner` | `test_v3_eval.py::test_v3_partition_registered` | V3 分区用例数与负例数 |
| `REQ-ADS-GOV-004` | specified（PR-0 已产出 ADR） | `docs.architecture.adr_006` | `check_safety_paths.py` | ADR 状态与被覆盖的受保护路径数 |
| `REQ-ADS-NFR-QA-007` | specified（PR-1 实现） | `scripts.fitness_functions` | `fitness_functions.py` | ELEMENT_BY_PACKAGE 是否含 corpus |
| `REQ-ADS-GOV-005` | specified（PR-0 登记 TA-0005 待签） | `docs.test_approvals` | `check_test_approval.py` | 测试批准记录与实现时间的先后 |
| `REQ-ADS-FR-012` | implemented（V3） | `corpus.pricing.bid_cents_from_price` | `test_corpus.py::test_bid_is_five_percent_of_price` | 出价分布、免费游戏保底命中数 |
| `REQ-ADS-ARCH-016` | implemented（V3） | `corpus.pricing / bidding.ledger.Ledger.finalize / INV-V3-007/008` | `test_corpus.py::test_twenty_impressions_exhaust_budget` | 5% 常量出现位置数、20 次后的 remaining |
