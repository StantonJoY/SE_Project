# 执行计划清单 · P7 — 固定评估集 + 版本溯源 + 变异验证

> **状态**：**✅ 已批准（2026-10-06，批准者 Shane）** · 实现中
> 模板：`docs/execution-plan-template.md` · 启动指令：`Prompt.md`
> 日期：2026-10-06 · 前置条件核对见 §6
>
> **MANDATE**：在获得明确批准之前，严格禁止输出源代码、修改文件或调用执行类工具。
> （例外：§5 步骤 0 的**文档登记**是本计划自身获批所需的前置动作，须与本计划一并批准。）

---

## ① Traceability

```yaml
task_id: "P7"
title: "建立可一键 replay 的固定评估集；补齐决策证据的版本溯源；建立变异验证以证明测试具备证伪能力"
round: "V1（docs/architecture/ 轮次）"

requirements:
  - "REQ-ADS-NFR-QA-001"   # 评估集 ≥ 20 条，一键 replay，输出通过率与违规数（主目标）
  - "REQ-ADS-NFR-QA-002"   # 每个 fit criterion ≥1 测试；每条不变量 ≥1 会失败的反例测试
  - "REQ-ADS-NFR-PERF-001" # p95 延迟监控 + SLA drift alert（四元素中缺的后两个，窗口=评估集 replay）
  - "REQ-ADS-AI-002"       # 决策证据须含 model_version + prompt_version + threshold

invariants:
  - "INV-ADS-011"   # 测试须具备证伪能力（变异验证）；缺口必须有去向
  - "INV-ADS-014"   # 评估集 replay 不得绕过上下文预算约束
  - "INV-ADS-016"   # 评估门：阈值失败必须阻断后续
  - "INV-ADS-012"   # 版本溯源字段须随审计记录一并落盘（恰好 1 条）

asrs:
  - "ASR-ADS-15"   # 固定评估集 + replay runner，作 CI 阻断门（QA-001 的承载）
  - "ASR-ADS-16"   # verification gate：fit criterion 覆盖 + 不变量失败测试（QA-002 的承载）
  - "ASR-ADS-11"   # timeout gate + fallback + p95 监控 + SLA drift alert（PERF-001 的承载）
  - "ASR-ADS-10"   # provenance 证据子系统（AI-002 的承载）

fit_criteria:
  - id: "FC-P7-01"
    condition: "eval/eval_cases.json 存在且用例数 ≥ 20（REQ-ADS-NFR-QA-001）"
  - id: "FC-P7-02"
    condition: "eval_runner 一键 replay 输出通过率与违规数，退出码反映阈值判定（QA-001）"
  - id: "FC-P7-03"
    condition: "每条用例含 expected（ad|no_ad）+ 判定标签 + 依据，且标签为封闭枚举（OQ-005）"
  - id: "FC-P7-04"
    condition: "replay 达成率 ≥ 0.95 视为通过；未达则 MUST_FAIL 用例之外的原因导致 → 阻断（自定阈值）"
  - id: "FC-P7-05"
    condition: "每条决策审计记录含 model_version + prompt_version + threshold（AI-002）"
  - id: "FC-P7-06"
    condition: "p95 延迟由 replay 计算并输出；超 5s 触发 sla_drift_alert 记录（PERF-001）"
  - id: "FC-P7-07"
    condition: "变异脚本对每条不变量注入违规，确认存在至少 1 个测试失败（QA-002 / INV-ADS-011）"
  - id: "FC-P7-08"
    condition: "MUST_FAIL 用例（预期降级）与 MUST_PASS 用例分别统计，失败即为有效观测而非阻断（人类指示）"

test_design: >-
  pytest（离线确定性，全部走 MockLLM）+ 两个独立可执行工具：
  `scripts/mutation_check.py`（变异验证）与 `eval/eval_runner.py`（评估集 replay）。
  二者均可作为 CI 步骤，且 replay 结果须写入 `eval/reports/`（append-only）。
```

**ID 真实性**：本计划引用的 REQ/INV/ASR **已逐条核实存在**：

| ID | 核实来源 |
|---|---|
| `REQ-ADS-NFR-QA-001` / `QA-002` / `PERF-001` / `AI-002` | `docs/req/requirements.yaml`（基线 22 条） |
| `INV-ADS-011` / `012` / `013` / `014` / `016` | `docs/architecture/invariants.md`（16 条） |
| `ASR-ADS-15`（评估集）/ `ASR-ADS-16`（verification gate）/ `ASR-ADS-11`（PERF 四元素）/ `ASR-ADS-10`（provenance） | `docs/architecture/asr-register.md`（18 ASR + 4 impl） |

三处双向一致性由 `scripts/validate_requirements.py` 强制（孤儿条目即 FAIL）。
**本计划不再需要"先确认再引用"的保留动作** —— 上表即为核实结果。

---

## ② Interface Contract

```yaml
elements:

  - file: "eval/__init__.py"
    note: "新顶层包（blueprint 目录树已规划 `eval/`）；仅作包标记，不含逻辑"

  - file: "eval/eval_cases.json"
    note: "固定评估集（数据文件，非代码）。≥20 条，结构与字段见下"

  - file: "eval/eval_runner.py"
    function: "main"
    docstring_ref: "REQ-ADS-NFR-QA-001 · INV-ADS-016 · ADR-002 D3"
    signature:
      params: {argv: "list[str] | None"}
      returns: "int"          # 退出码：0 = 达成率 ≥ 阈值；1 = 未达；2 = 配置/数据错误
      raises: ["[]"]
    contract: >-
      **一键 replay**：读取 eval/eval_cases.json，对每条用例跑 **完整管道**
      （`app.pipeline.recommend`，注入 MockLLM），比对 `expected`，
      输出：用例总数、MUST_PASS 达成率、MUST_FAIL 达成数、
      违规数（越权展示 / 审计条数 ≠ 1 / schema 失败）、p95 延迟。
      **不读写除 eval/ 与 logs/ 之外的文件；不调网络。**

  - file: "eval/eval_runner.py"
    function: "load_cases"
    docstring_ref: "REQ-ADS-NFR-QA-001"
    signature:
      params: {path: "str | Path"}
      returns: "list[EvalCase]"
      raises: ["EvalDataError"]
    contract: >-
      **fail-closed 校验**：JSON 非数组 / 用例缺字段 / expected 非 {ad,no_ad} /
      label 不在封闭枚举内 / 引用了素材库中不存在的 ad_id → 一律抛 EvalDataError。
      与 `BannedWords.load` 同姿态（`BUG-007` 的教训）。

  - file: "src/app/pipeline.py"          # 修改（非新建）
    function: "recommend"
    change: "审计记录的 `threshold` 分支补 prompt_version 与 model_version；新增 provenance 段"
    docstring_ref: "REQ-ADS-AI-002 · INV-ADS-012"
    contract: >-
      新增审计字段 `provenance = {model_version, prompt_version, threshold}`。
      **model_version 与 prompt_version 的来源**：V1 无真实 prompl 文件，
      故取值规则为 —— `model_version` = `config.llm.provider/model`（如 `mock/`），
      `prompt_version` = 上下文装配的 prompt 指纹（`context.py` 暴露的常量版本号，
      见下方 context 变更）。**不得写入无意义的空字符串**：缺失时写 `"unknown"` 并
      计入 monitor `decisions_missing_version_provenance`。

  - file: "src/selector/context.py"      # 修改（本元素属 P4 已交付，改动需说明）
    change: "导出 PROMPT_TEMPLATE_VERSION 常量（六层模板的版本号）"
    docstring_ref: "REQ-ADS-AI-002"
    contract: "纯增量：新增模块级常量，不改变任何既有函数签名或行为"

  - file: "scripts/mutation_check.py"
    function: "main"
    docstring_ref: "REQ-ADS-NFR-QA-002 · INV-ADS-011"
    signature:
      params: {argv: "list[str] | None"}
      returns: "int"          # 0 = 每条不变量都有会失败的测试；1 = 存在"从未失败"的不变量
      raises: ["[]"]
    contract: >-
      **对每条已声明 `negative_test_backed: true` 的不变量**：
      按 `MUTATIONS` 表中登记的变异操作（如把 `compliance.check_category` 恒返回通过）
      在**内存中的副本**上注入违规，运行相关测试子集，**确认至少 1 个测试失败**。
      若某不变量注入后测试**仍然全绿** → 该"反例测试"不具备证伪能力 → FAIL。
      **绝不修改仓库中的源文件**（用 monkeypatch / 临时模块替换），失败后必定还原。

shared_shapes:
  EvalCase:
    id: "str（形如 EC-001）"
    scene: "{time_slot, device, user_tags}"
    expected: "ad | no_ad"
    label: "MUST_PASS | MUST_FAIL | MUST_FAIL_ON_REPLAY"
    expect_reason: "str | null（expected=no_ad 时给出理由码，可为 null 表示任一）"
    expected_category: "str | null（expected=ad 时的品类约束，OQ-005 = 甲/混合）"
    expected_ad_id: "str | null（人工标注的正确答案；null 表示只校验品类与合规）"
    basis: "str（这条用例的依据：哪条 REQ/ASR/不变量，或哪个真实失败场景）"
    anchors: "list[str]（该用例守护的 REQ/INV ID）"
```

**签名自检**：`eval_runner` 调用 `app.pipeline.recommend` 的既有签名不变；
`context.py` 仅新增常量（纯增量）；`pipeline.py` 仅新增审计字段（不改降级语义）。

---

## ③ Scope Boundaries

```yaml
target_files:
  # 新建
  - "eval/__init__.py"
  - "eval/eval_cases.json"
  - "eval/eval_runner.py"
  - "eval/reports/.gitkeep"                 # replay 报告目录（append-only）
  - "scripts/mutation_check.py"
  - "test/offline/test_eval_runner.py"
  - "test/offline/test_mutation_check.py"
  - "test/offline/test_provenance.py"       # AI-002 的版本溯源
  # 修改（最小、增量）
  - "src/selector/context.py"               # 仅新增 PROMPT_TEMPLATE_VERSION
  - "src/app/pipeline.py"                   # 仅新增 provenance 审计字段
  - "config.yaml"                           # 新增 eval 段（阈值 0.95、预算）
  # 文档登记（步骤 0，须与本计划一并批准）
  - "architecture-blueprint.md"             # §4 补 eval/ 元素行
  - "AGENTS.md"                             # ④ 补 eval/ 与 scripts/ 角色；③ 权限表补 eval/
  - "docs/req/requirements.yaml"            # OQ-005 关闭 + resolution
  - "docs/code-governance/acceptance-coverage-map.yaml"   # QA-001/002、AI-002、PERF-001 更新
  - "docs/architecture/trace-matrix.md"     # Status 更新
  - "docs/debt-register.md"                 # 关闭/新增相关条目
  - "docs/ai-use-log.yaml"                  # 门禁 6

allowed_imports:
  - "json"            # 评估集与报告
  - "argparse"
  - "statistics"      # p95 计算（quantiles）
  - "time"            # 延迟测量
  - "subprocess"      # **仅** mutation_check.py 运行 pytest 子集
  - "importlib"
  - "typing"
  - "dataclasses"
  - "pathlib"
  - "app"             # 管道
  - "selector"        # MockLLM + 常量
  - "ads" / "compliance" / "audit" / "render"
  - "pytest"          # 仅测试与变异脚本

prohibited_imports:
  - "requests" / "httpx" / "openai" / "urllib" / "socket"   # 禁止网络（P8 才接真实 LLM）
  - "os.environ"      # 不得依赖环境变量（配置只走 config.yaml）

data_access:
  read: ["eval/eval_cases.json", "config.yaml", "data/*.json（经既有 Repository/Rules 加载器）"]
  write: ["eval/reports/（replay 报告，append-only）", "logs/audit.jsonl（经既有 AuditStore）"]

frozen_paths_not_touched:
  - "src/ads/"
  - "src/scene/"
  - "src/compliance/"        # compliance 是 FINAL AUTHORITY，本轮绝不改动
  - "data/"                  # 素材与词表不因评估集而改动
  - "docs/architecture/invariants.md"
```

**安全路径自检**：`scripts/check_safety_paths.py --show-paths` 的 9 条受保护路径中，
本计划**只触及** `docs/req/requirements.yaml`（登记 `OQ-005` 关闭）
与 `src/selector/`（清单项为"改动**阈值逻辑**时须 ADR"——本计划**不**改阈值逻辑，
仅新增常量）。

> ⚠️ **门禁 2 的真实冲突（已实测，非推测）**：`check_safety_paths.py` 对
> `docs/req/requirements.yaml` 报 **FAIL** —— 该路径标记为"须 ADR"，
> 而检查器要求**新增/修改 ADR 文件**或在**提交信息中引用 ADR ID**。
>
> 本计划对该文件的改动是**关闭 `OQ-005` 并记录 resolution**，
> 属于已批准计划的步骤 0，**不是新的架构决策**。
> **处置**：提交时在 commit message 中引用 `ADR-002`（其 §2 D4 正是该路径的保护来源），
> 以引用而非新建 ADR 的方式满足检查器。**不新造 ADR**（那会假装这是新决策）。
> 若你希望改为新建一份 ADR-003，请明确告知。

**新增顶层包的处置**（`AGENTS.md` ⑦）：`eval/` 在 `blueprint` 的目录树中**已规划**，
非意外新增；且 S1 检查仅扫描 `src/`（`SRC = ROOT / "src"`），故不影响 S1。
**但**为消除文档与实现的漂移，步骤 0 必须把 `eval/` 补入 blueprint §4 与 `AGENTS.md` ④。

---

## ④ Testing Strategy

```yaml
cases:
  # ---- 评估集加载与结构（eval_runner） ----
  - name: "test_load_cases_ok"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "unit"
  - name: "test_eval_set_has_at_least_20_cases"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "unit"
    note: "硬门槛：< 20 条即失败（fit criterion 逐字要求）"
  - name: "test_every_case_has_required_fields"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "unit"
  - name: "test_reject_non_array_json"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "negative"
    invariant_covered: "INV-ADS-011"
  - name: "test_reject_unknown_expected_value"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "negative"
  - name: "test_reject_unknown_label"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "negative"
  - name: "test_reject_ad_id_absent_from_repository"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "negative"
    note: "防止标注了一个素材库中不存在的正确答案（死标注）"
  - name: "test_case_ids_are_unique"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "unit"

  # ---- replay 行为 ----
  - name: "test_replay_all_cases_returns_report"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "unit"
  - name: "test_report_reports_pass_rate_and_violations"
    anchors: ["REQ-ADS-NFR-QA-001", "INV-ADS-016"]
    type: "unit"
  - name: "test_exit_code_reflects_threshold"
    anchors: ["INV-ADS-016"]
    type: "unit"
    note: "达成率 < 阈值 → 退出码 1（评估门必须能阻断）"
  - name: "test_must_fail_cases_are_counted_separately"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "unit"
    note: "人类指示：MUST_FAIL 用例是**有效观测**，不是阻断理由"
  - name: "test_replay_is_deterministic"
    anchors: ["REQ-ADS-ARCH-004"]
    type: "deterministic_replay"
  - name: "test_replay_writes_report_to_reports_dir"
    anchors: ["REQ-ADS-NFR-QA-001"]
    type: "unit"
    note: "报告须 append-only（不覆盖历史），用 I/O 边界打桩（不用 tmp_path）"

  # ---- 违规计数（评估集的真正价值） ----
  - name: "test_violation_count_zero_on_clean_run"
    anchors: ["INV-ADS-001"]
    type: "unit"
  - name: "test_out_of_candidate_selection_is_a_violation"
    anchors: ["INV-ADS-002"]
    type: "negative"
    invariant_covered: "INV-ADS-002"
  - name: "test_audit_count_not_one_is_a_violation"
    anchors: ["INV-ADS-012"]
    type: "negative"
    invariant_covered: "INV-ADS-012"

  # ---- p95 与 SLA（PERF-001 的后两个元素） ----
  - name: "test_p95_computed_from_replay_latencies"
    anchors: ["REQ-ADS-NFR-PERF-001"]
    type: "unit"
  - name: "test_sla_drift_alert_recorded_when_p95_exceeds"
    anchors: ["REQ-ADS-NFR-PERF-001"]
    type: "negative"
    invariant_covered: "INV-ADS-013"

  # ---- 版本溯源（AI-002） ----
  - name: "test_audit_record_contains_provenance"
    anchors: ["REQ-ADS-AI-002"]
    type: "unit"
  - name: "test_provenance_missing_is_recorded_as_unknown_not_empty"
    anchors: ["REQ-ADS-AI-002"]
    type: "negative"
    invariant_covered: "INV-ADS-012"
    note: "禁止写空字符串掩盖缺失；缺失必须是显式 unknown（可被 monitor 统计）"
  - name: "test_prompt_template_version_constant_exists"
    anchors: ["REQ-ADS-AI-002"]
    type: "unit"

  # ---- 变异验证（QA-002 / INV-ADS-011） ----
  - name: "test_mutation_table_covers_all_negative_backed_invariants"
    anchors: ["REQ-ADS-NFR-QA-002", "INV-ADS-011"]
    type: "unit"
    note: "防止变异表与覆盖表漂移：声明为 backed 的不变量必须有对应变异"
  - name: "test_mutated_compliance_is_detected_by_tests"
    anchors: ["INV-ADS-001", "INV-ADS-011"]
    type: "negative"
    invariant_covered: "INV-ADS-011"
    note: "**本计划最重要的一条**：把 compliance 变异为恒通过，必须导致测试失败"
  - name: "test_mutation_restores_original_code"
    anchors: ["INV-ADS-011"]
    type: "unit"
    note: "变异脚本必须保证还原（否则会污染仓库）"
  - name: "test_mutation_check_reports_invariant_without_failing_test"
    anchors: ["INV-ADS-011"]
    type: "negative"
    note: "构造一个'注入违规但测试仍全绿'的假不变量，脚本必须报 FAIL"
```

**硬性遵守**（`docs/code-governance/verification-constraints.md`）：

- ✅ 每条 fit criterion ≥ 1 测试（V1）
- ✅ 被覆盖的不变量 ≥ 1 个**会失败**的反例测试（V2），且测试 docstring 含"反例"标记
- ✅ 测试 docstring 引用 REQ/INV ID（V3）
- ✅ **不使用 pytest `tmp_path`**（受限沙箱；用 I/O 边界打桩）
- ⚠️ **门禁 1：本计划的测试须在实现开始前登记并获批**（§5 步骤 1，此为 `TD-023` 的纠正动作）

---

## ⑤ Implementation Steps

```yaml
steps:
  - "0. 【文档登记，须与本计划一并批准】
       · architecture-blueprint.md §4 补 eval/ 元素行（消除文档漂移）
       · AGENTS.md ④ 补 eval/ 与 scripts/mutation_check.py 的角色；③ 权限表补 eval/
       · docs/req/requirements.yaml：关闭 OQ-005 并写 resolution
         （口径 = agent 自造为主 + 人类审查后可增改；通过率阈值 95%；FAIL 亦为有效观测）
       · 顺带处理 TD-024（AGENTS.md ④ 的 config.py / __main__.py 缺口）"
  - "1. 【门禁 1：测试先获批】在 docs/test-approvals.yaml 登记本计划 §4 的测试文件与
       req_ids，取得具名批准（TA-0004, pre_registered: true, 指向本计划）。
       **未完成前不得进入步骤 2** —— 这是 TD-023 的纠正动作。"
  - "2. 建 eval/ 包骨架：__init__.py、reports/.gitkeep。"
  - "3. 编写 eval/eval_cases.json（21 条，五类：正常 MUST_PASS 6 条、
      降级 MUST_FAIL 7 条、合规对抗 4 条、注入 2 条、边界 2 条）。
      每条含 basis 与 anchors；expected_ad_id 由我标注，人类后续审查可增改。"
  - "4. 实现 eval/eval_runner.py：load_cases（fail-closed 校验）+ replay（跑完整管道）
      + 报告（通过率/违规数/p95/MUST_FAIL 计数）+ 退出码 + append-only 报告落盘。"
  - "5. src/selector/context.py 新增 PROMPT_TEMPLATE_VERSION 常量（纯增量）。"
  - "6. src/app/pipeline.py 审计记录新增 provenance 段（model_version / prompt_version /
      threshold）；缺失写 'unknown' 并计入 decisions_missing_version_provenance。"
  - "7. config.yaml 新增 eval 段（pass_rate_threshold: 0.95、latency_p95_threshold_sec: 5）。"
  - "8. 实现 scripts/mutation_check.py：MUTATIONS 表（每条 negative_test_backed 不变量
      一条变异）+ 注入 + 跑相关测试子集 + 断言至少 1 个失败 + 必定还原。"
  - "9. 补 3 个测试模块（test_eval_runner / test_mutation_check / test_provenance），
      按 §4 清单，docstring 引用 REQ/INV。"
  - "10. 同步治理工件：acceptance-coverage-map.yaml（QA-001/002、AI-002、PERF-001 转 backed）、
      trace-matrix.md（Status）、debt-register.md（关 TD-003/TD-023 相关、新立遗留）、
      ai-use-log.yaml（门禁 6）。"
  - "11. 首次真正行使门禁 4：python scripts/check_semantic_eval.py 应识别评估集并运行 replay。"

verification_after_each_step:
  - "每步后：pytest test/offline -q（零回归）"
  - "步骤 4 后：python eval/eval_runner.py（一键 replay 必须可跑通并输出报告）"
  - "步骤 8 后：python scripts/mutation_check.py（每条不变量都有会失败的测试）"
  - "步骤 9 后：ruff check src test scripts eval && mypy"
  - "步骤 10 后：validate_requirements.py && fitness_functions.py && check_ai_use_log.py
      && audit_implementation.py"
  - "步骤 11 后：check_semantic_eval.py --files prompts/x.yaml（应因缺少 prompt 而
      **不再**以'评估集不存在'为由阻断，而是走到 replay 分支）"

rollback: >-
  eval/ 为全新目录，删除即可；scripts/mutation_check.py 与 3 个测试模块为新建；
  context.py 与 pipeline.py 的改动是**纯增量**（新增常量与新增审计字段），
  回滚 = 移除新增行 + revert config.yaml 与文档登记。
  **变异脚本必须自带还原**（try/finally），失败也不得留下被改动的源文件。
```

---

## ⑥ 前置条件核对

| 前置条件 | 状态 | 是否阻塞 |
|---|---|---|
| `ADR-001` / `ADR-002` | ✅ `Accepted`（Shane） | ❌ |
| `OQ-005`（评估集口径） | ⏳ **待本计划一并关闭** | ✅ **阻塞步骤 3** |
| 门禁 1 具名批准者 | ✅ 已填（Shane） | ❌（但本计划测试须先获批） |
| `eval/` 是否已规划 | ✅ blueprint 目录树已含 | ❌ |

**人类决定（2026-10-06）**：
- **`OQ-005` 口径** = **由 agent 自造为主，人类审查后可增改**；
  即每条用例含人工标注的 `expected_ad_id`（强信号），但标注由 agent 产出、
  人类审查 —— 记作 **甲/混合** 方案。
- **通过率阈值 = 0.95**（人类指示：仅做 demo；**FAIL 也是一种情况**，
  故 MUST_FAIL 用例单独统计、不作为阻断理由）。

---

## ⑦ 人工批准记录

| 项 | 内容 |
|---|---|
| 计划文件 | `docs/plans/P7-eval.md` |
| 提交评审时间 | 2026-10-06 |
| **批准者（具名人类）** | **Shane** |
| 批准时间 | **2026-10-06** |
| 批准结论 | ✅ **APPROVED** |
| 修订次数 | 0 |

> **批准记录**：人类于 2026-10-06 表示「批准」，同时确认两项决定：
> ① `OQ-005` 口径 = **agent 自造为主 + 人类审查后可增改**；
> ② 通过率阈值 = **0.95**（仅做 demo；**FAIL 也是一种情况**，故 `MUST_FAIL` 单独统计）。
> **No agent may self-approve**（课程 §11.3）——本次批准由人类做出。
>
> **本计划的额外意义**：本轮是 `TD-023` 的**纠正轮**。
> P5/P6 跳过了"计划 → 批准 → 测试先获批"的链条；本计划要求链条完整恢复，
> 以证明该流程在本项目中**可被遵守**，而非只在 P4 被遵守过一次。

## ⑧ 执行进度

| # | 步骤 | 状态 |
|---|---|---|
| 0 | 文档登记（blueprint / AGENTS.md / requirements.yaml）+ 关闭 `OQ-005` | ⏳ 进行中 |
| 1 | 门禁 1：登记 P7 测试为 `TA-0004` 并获批 | ⏳ |
| 2 | `eval/` 包骨架 | ⏳ |
| 3 | `eval/eval_cases.json`（21 条，五类） | ⏳ |
| 4 | `eval/eval_runner.py` | ⏳ |
| 5–7 | 版本溯源（`context.py` / `pipeline.py` / `config.yaml`） | ⏳ |
| 8 | `scripts/mutation_check.py` | ⏳ |
| 9 | 三个测试模块 | ⏳ |
| 10 | 治理工件同步 | ⏳ |
| 11 | 门禁 4 首次真正生效 | ⏳ |
