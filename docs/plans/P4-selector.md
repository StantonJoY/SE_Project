# 执行计划清单 · P4 — `src/selector/` AI 建议层

> **状态**：**待人工批准**（未获批前不得写任何代码）
> 模板：`docs/execution-plan-template.md` · 启动指令：`Prompt.md`
> 日期：2026-10-06 · 前置条件核对见 §6

**MANDATE**：在获得明确批准之前，严格禁止输出源代码、修改文件或调用执行类工具。

---

## ① Traceability

```yaml
task_id: "P4"
title: "实现 AI 建议层：闭集选择 + 严格 JSON 解析 + 六层上下文装配 + 解释路径隔离"
round: "V1（docs/architecture/ 轮次）"

requirements:
  - "REQ-ADS-ARCH-002"      # 闭集选择：LLM 只能从候选集内选
  - "REQ-ADS-ARCH-003"      # 输出必须为合法结构化 JSON
  - "REQ-ADS-ARCH-004"      # 确定性可复现（MockLLM 同输入同输出）
  - "REQ-ADS-NFR-SAFETY-005" # 低置信度不得直接展示（本层**上报** confidence，判定在 app）
  - "REQ-ADS-NFR-COST-001"  # token 预算 + compaction 后重注入
  - "REQ-ADS-AI-001"        # 解释路径与决策路径结构分离

invariants:
  - "INV-ADS-002"   # AI 绝不在候选集之外选择（本层在解析期拒绝集外 ad_id）
  - "INV-ADS-003"   # 非法 LLM 输出绝不进入决策（本层 fail-closed）
  - "INV-ADS-004"   # 解释路径绝不影响决策（本层实现隔离）
  - "INV-ADS-014"   # 上下文预算绝不被突破；关键约束绝不因压缩而消失

asrs:
  - "ASR-ADS-02"    # 候选集 wrapper + 存在性 gate
  - "ASR-ADS-03"    # validation gate + fail-closed
  - "ASR-ADS-08"    # threshold gate（上报侧）
  - "ASR-ADS-14"    # budget route + summarization gate
  - "ASR-ADS-A3-01" # 六层上下文 + 五步装配 + 85% compaction + re-injection
  - "ASR-ADS-A3-02" # 解释路径隔离

fit_criteria:
  - id: "FC-P4-01"
    condition: "parse_llm_output 对合法 JSON 返回合法 judgment（REQ-ADS-ARCH-003）"
  - id: "FC-P4-02"
    condition: "候选集外的 ad_id 被拒绝，违反数 = 0（REQ-ADS-ARCH-002 / INV-ADS-002）"
  - id: "FC-P4-03"
    condition: "畸形 JSON 重试 1 次后降级，不抛未处理异常（INV-ADS-003）"
  - id: "FC-P4-04"
    condition: "解释质量不达标时 ad_id 不变；解释含违禁词时被剥离（INV-ADS-004）"
  - id: "FC-P4-05"
    condition: "装配后 token ≤ 预算；compaction 后 standing constraints 仍在最终 prompt 中（INV-ADS-014）"
  - id: "FC-P4-06"
    condition: "同输入重复调用输出逐位一致（REQ-ADS-ARCH-004）"

test_design: "pytest + MockLLM（离线确定性，不调任何真实 API）"
```

**ID 真实性自检**：以上全部 ID 已在 `python scripts/validate_requirements.py` 中通过双向一致性校验
（注册表 ↔ `asr-register.md` ↔ `invariants.md`，孤儿条目即报错）。

---

## ② Interface Contract

```yaml
elements:

  - file: "src/selector/__init__.py"
    note: "包初始化；当前该目录**完全为空**（连 __init__.py 都没有），本步创建并导出公共 API"

  - file: "src/selector/client.py"
    class: "LLMClient"                     # typing.Protocol
    implements: "Protocol（结构化子类型）"
    docstring_ref: "ADR-001（AI is advisory）· REQ-ADS-ARCH-002"
    public_methods:
      - name: "select"
        params: {prompt: "str"}
        returns: "str"                     # LLM 的**原始文本**，本层不解析
        raises: ["LLMUnavailable"]         # 超时/不可用（由 ADR-002 D1 降级）

  - file: "src/selector/client.py"
    class: "MockLLM"
    implements: "LLMClient"
    docstring_ref: "ADR-005 原则（离线一律 MockLLM）· REQ-ADS-ARCH-004"
    public_methods:
      - name: "select"
        params: {prompt: "str"}
        returns: "str"
        raises: ["LLMUnavailable"]         # 可由构造参数注入失败，用于测试降级路径
    contract: >-
      **确定性**：同一 prompt 必返回同一原始文本（无随机、无时间依赖）。
      默认可从 prompt 中解析出候选 ad_id 列表并选择**字典序最小**者，
      confidence 为固定值（可由构造参数指定）。

  - file: "src/selector/parser.py"
    function: "parse_llm_output"
    docstring_ref: "ADR-001 §2（严格 JSON gate）· INV-ADS-003 · REQ-ADS-ARCH-003"
    signature:
      params: {raw: "str", candidate_ids: "Sequence[str]"}
      returns: "OutputJudgment"
      raises: ["LLMOutputError"]
    contract: >-
      **fail-closed**：非 JSON、缺字段、类型错、confidence 越界 [0,1]、
      或 ad_id 不在 candidate_ids 中 —— 一律抛 LLMOutputError（由上层重试 1 次后降级）。
      **本函数是"闭集"的执行点**：集外 ad_id 在此被拒（INV-ADS-002）。

  - file: "src/selector/parser.py"
    class: "LLMOutputError"
    base: "Exception"

  - file: "src/selector/context.py"
    function: "route_budget"
    docstring_ref: "ASR-ADS-14 · RP-010"
    signature:
      params: {estimated_tokens: "int", budget: "int"}
      returns: "BudgetDecision"
    contract: "三档确定性路由：DIRECT / SUMMARIZE / (超上限时) OVER_BUDGET"

  - file: "src/selector/context.py"
    class: "ContextAssembler"
    docstring_ref: "ASR-ADS-A3-01 · INV-ADS-014"
    public_methods:
      - name: "assemble"
        params: {scene_summary: "str", candidates: "list[CandidateBrief]", task: "str"}
        returns: "AssembledContext"
        raises: ["[]"]
    contract: >-
      按**五步装配管线**：DEDUPLICATE → PRIORITIZE → BUDGET → COMPACT → ASSEMBLE。
      六层：SYSTEM / INSTRUCTIONS / RETRIEVED / HISTORY（V1 不适用，显式标注）/
      STATE / USER。
      **compaction 后必须重新注入层 2 的 standing constraints**（INV-ADS-014）。
      HISTORY 层在 V1 为空，但**必须显式存在并标注"不适用 + 理由"**，不得默默省略。

  - file: "src/selector/explanation.py"
    function: "generate_explanation"
    docstring_ref: "ASR-ADS-A3-02 · INV-ADS-004 · REQ-ADS-AI-001"
    signature:
      params: {judgment: "OutputJudgment", candidates: "list[CandidateBrief]"}
      returns: "Explanation"
      raises: ["[]"]
    contract: >-
      解释口径 = **「为什么选这条广告」**（OQ-009，2026-10-06 已确认）：
      须说明在当前场景特征下，为何选该广告**而非候选集中的其他广告**。
      **只读**：不得接收也不得返回可写决策的句柄。

  - file: "src/selector/explanation.py"
    function: "verify_explanation"
    docstring_ref: "INV-ADS-004 · INV-ADS-007（复查）· RP-012"
    signature:
      params: {explanation: "Explanation", banned_words: "BannedWords" }
      returns: "VerifiedExplanation"
      raises: ["[]"]
    contract: >-
      违规解释被**剥离**（返回降级后的结构化摘要），
      **绝不改写传入的 ad_id**（函数无此返回值）。
```

**共享数据形状**（定义在 `client.py` 或独立小模块，避免循环导入）：

```yaml
CandidateBrief:   {ad_id: str, title: str, category: str, target_tags: list[str]}
OutputJudgment:   {ad_id: str, reason: str, confidence: float}
AssembledContext: {prompt: str, layers: dict[str, str], compacted: bool, tokens: int, decisions: list[str]}
Explanation:      {ad_id: str, text: str, degraded: bool}
```

**签名自检**：与 `AGENTS.md` ④（模块组织表 4 个文件）与 ⑤（集成契约：
`app.pipeline` → `selector.context.assemble` 在 LLM **之前**；
`app.pipeline` → `selector.parser.parse_llm_output` 在 LLM **之后**；
`app.pipeline` → `selector.explanation` 在决策 **之后**）一致。

---

## ③ Scope Boundaries

```yaml
target_files:
  - "src/selector/__init__.py"     # 新建
  - "src/selector/client.py"       # 新建
  - "src/selector/parser.py"       # 新建
  - "src/selector/context.py"      # 新建
  - "src/selector/explanation.py"  # 新建
  # 测试（允许新建）
  - "test/offline/test_selector.py"
  - "test/offline/test_context_assembly.py"
  - "test/offline/test_explanation.py"
  # 治理工件（必须同步更新，否则门禁阻断）
  - "docs/ai-use-log.yaml"                              # 门禁 6
  - "docs/code-governance/acceptance-coverage-map.yaml"  # V1/V2 覆盖
  - "docs/architecture/trace-matrix.md"                  # Status: design → tested
  - "docs/debt-register.md"                              # 关闭 TD-020 的 selector 部分

allowed_imports:
  - "typing"            # Protocol / Sequence / dataclass
  - "dataclasses"
  - "json"
  - "re"                # 仅用于从 prompt 中提取候选 ID（MockLLM）
  - "jsonschema"        # 已声明的运行时依赖
  - "ads"               # 只读：Ad / BannedWords 类型
  - "ads.banned_words"

prohibited_imports:
  - "os"                # 禁止环境探测
  - "subprocess"
  - "requests"          # 禁止网络
  - "httpx"
  - "openai"            # 禁止真实 LLM SDK（P8 再做，届时需 ADR）
  - "urllib"
  - "socket"
  - "pathlib"           # selector **不得写文件**（审计归 src/audit/）
  - "io"
  - "src.compliance"    # 反向依赖禁止：selector 不得调用 compliance
  - "compliance"        # （同上；违反则权威边界倒置）

data_access:
  read: ["config.yaml（selector.confidence_threshold / llm.timeout_sec / 上下文预算）"]
  not_read: ["data/*.json 直接读取 —— 候选集必须由调用方经 AdRepository 传入"]
  write: []             # 本层不写任何数据

frozen_paths_not_touched:
  - "src/ads/"
  - "src/scene/"
  - "src/compliance/"
  - "data/"
  - "docs/req/requirements.yaml"
  - "docs/architecture/invariants.md"
```

**安全路径自检**：`src/selector/` **在受保护清单中**（`ADR-002` §2 D4：改动阈值逻辑时须 ADR）。
本计划**不修改** `config.yaml`（阈值 0.5 已定案），只**读取**，
故不触发现有阈值逻辑。若批准时要求改动阈值语义，则须先补 ADR。

**禁止路径核对**（`scripts/check_safety_paths.py --show-paths` 的 9 条）：
本计划的 `target_files` 与其中任何一条**均不相交**（`src/selector/` 清单项为"改动阈值逻辑时须 ADR"，
本计划不改阈值）。

---

## ④ Testing Strategy

```yaml
cases:
  # ---- 解析与闭集（parser） ----
  - name: "test_parse_valid_json_ok"
    fit_criterion: "FC-P4-01"
    type: "unit"
    invariant_covered: null
  - name: "test_parse_rejects_out_of_candidates"
    fit_criterion: "FC-P4-02"
    type: "negative"          # 反例：集外 ad_id 必须被拒
    invariant_covered: "INV-ADS-002"
  - name: "test_parse_rejects_malformed_json"
    fit_criterion: "FC-P4-03"
    type: "negative"
    invariant_covered: "INV-ADS-003"
  - name: "test_parse_rejects_missing_and_wrong_type_fields"
    fit_criterion: "FC-P4-03"
    type: "negative"
    invariant_covered: "INV-ADS-003"
  - name: "test_parse_rejects_confidence_out_of_range"
    fit_criterion: "FC-P4-03"
    type: "negative"
    invariant_covered: "INV-ADS-003"
  - name: "test_parse_is_deterministic"
    fit_criterion: "FC-P4-06"
    type: "deterministic_replay"
    invariant_covered: "INV-ADS-003"

  # ---- 上下文装配（context） ----
  - name: "test_route_budget_three_tiers"
    fit_criterion: "FC-P4-05"
    type: "unit"
    invariant_covered: null
  - name: "test_assembled_tokens_within_budget"
    fit_criterion: "FC-P4-05"
    type: "unit"
    invariant_covered: "INV-ADS-014"
  - name: "test_compaction_reinjects_standing_constraints"
    fit_criterion: "FC-P4-05"
    type: "negative"          # 反例：压缩后若约束消失即为违规
    invariant_covered: "INV-ADS-014"
  - name: "test_history_layer_explicitly_marked_not_applicable"
    fit_criterion: "FC-P4-05"
    type: "unit"
    note: "六层必须显式存在；HISTORY 为空但须标注『不适用 + 理由』"

  # ---- 解释路径（explanation） ----
  - name: "test_explanation_degradation_keeps_ad_id"
    fit_criterion: "FC-P4-04"
    type: "negative"
    invariant_covered: "INV-ADS-004"
  - name: "test_explanation_with_banned_word_is_stripped"
    fit_criterion: "FC-P4-04"
    type: "negative"
    invariant_covered: "INV-ADS-004"

  # ---- MockLLM 确定性 ----
  - name: "test_mock_llm_deterministic"
    fit_criterion: "FC-P4-06"
    type: "deterministic_replay"
    invariant_covered: "INV-ADS-003"
    mock: "MockLLM"

  # ---- 阈值常量与 config 同步（防止 OQ-004 的结果静默漂移） ----
  - name: "test_config_threshold_matches_confirmed_decision"
    fit_criterion: "FC-P4-06"
    type: "unit"
    note: >-
      断言 config.yaml 的 selector.confidence_threshold == 0.5（OQ-004 的定案值）。
      若未来改阈值而未同步需求记录，本测试失败 —— 使"配置与决策记录漂移"可见。
```

**硬性遵守**（`docs/code-governance/verification-constraints.md`）：

- ✅ 每条 fit criterion ≥ 1 测试（V1）
- ✅ 每条被覆盖的不变量 ≥ 1 个**会失败**的反例测试（V2）——`INV-ADS-002/003/004/014` 均有
- ✅ 每个测试 docstring **引用其 REQ/INV ID**（V3）
- ✅ **不使用 pytest `tmp_path`**（受限沙箱兼容）
- ✅ 未覆盖项（如 `INV-ADS-006` 的完整判定依赖 `app`）在 `acceptance-coverage-map.yaml` 登记去向
- ⚠️ **测试先于实现获批**（门禁 1）：本计划的测试**须在实现开始前**登记于
  `docs/test-approvals.yaml` 并取得具名批准 —— **这是本计划获批后的第一个动作**

---

## ⑤ Implementation Steps

```yaml
steps:
  - "1. 前置：在 docs/test-approvals.yaml 登记本计划的测试文件并取得具名批准（门禁 1）。
        未完成前不得进入步骤 2。"
  - "2. 创建 src/selector/__init__.py（包初始化，docstring 引用 ADR-001 / REQ-ADS-ARCH-002），
        导出 ② 的公共 API 符号。"
  - "3. 实现 src/selector/client.py：LLMClient Protocol + MockLLM（确定性；可注入失败）。"
  - "4. 实现 src/selector/parser.py：LLMOutputError + OutputJudgment + parse_llm_output
        （严格 JSON + 字段类型 + confidence 范围 + 候选集存在性；穷举 fail-closed 分支）。"
  - "5. 实现 src/selector/context.py：CandidateBrief + BudgetDecision + route_budget（三档）
        + ContextAssembler.assemble（DEDUPLICATE→PRIORITIZE→BUDGET→COMPACT→ASSEMBLE，
        六层含显式 HISTORY 不适用标注，compaction 后重注入层 2 约束）。"
  - "6. 实现 src/selector/explanation.py：Explanation + generate_explanation（只读）
        + verify_explanation（违禁词剥离；不改 ad_id）。"
  - "7. 按 ④ 编写三个测试模块，每个测试 docstring 引用 REQ/INV ID。"
  - "8. 同步治理工件：ai-use-log.yaml（追加 entry）、acceptance-coverage-map.yaml
        （REQ-ADS-ARCH-002/003、NFR-SAFETY-005、NFR-COST-001、AI-001 → test_backed: true）、
        trace-matrix.md（对应 Status → tested）、debt-register.md（更新 TD-020）。"

verification_after_each_step:
  - "每一步后：pytest test/offline -q（零回归）"
  - "步骤 2 后：python scripts/fitness_functions.py（S1 一个元素一个模块、S3 docstring 可追溯性）"
  - "步骤 6 后（全部代码就位）：ruff check src test scripts && mypy"
  - "步骤 7 后：python scripts/fitness_functions.py（V1/V2/V3 覆盖）"
  - "步骤 8 后：python scripts/validate_requirements.py && python scripts/check_ai_use_log.py
        && python scripts/audit_implementation.py"

rollback: >-
  全部 target_files 除治理工件外均为**新建文件**；回滚 = 删除 src/selector/*.py 与三个
  测试模块，并 revert 四个治理工件的改动。不涉及数据迁移、不涉及既有文件改写，
  故回滚无残留状态。若任一验证失败：先 revert 到上一步，再修订计划（不得跳到代码）。
```

---

## ⑥ 前置条件核对（本计划起草时）

| 前置条件 | 状态 | 是否阻塞本计划 |
|---|---|---|
| `ADR-001`（Guarded Hybrid） | ⏳ `Proposed` | ✅ **阻塞实现**（本计划可获批，但实现前须 Accepted） |
| `ADR-002`（fail-closed 与治理） | ⏳ `Proposed` | ✅ **阻塞实现** |
| `OQ-009`（"解释"口径） | ✅ **已关闭**（2026-10-06） | ❌ 不阻塞 |
| `OQ-004`（confidence 阈值） | ✅ **已关闭** = 0.5（2026-10-06） | ❌ 不阻塞 |
| 门禁 1 具名批准者 | ✅ 已填（`Shane`，`TA-0001`） | ❌ 不阻塞，但**本计划的测试须先获批准** |

**结论**：本计划**已获批准**（见 §7）。前置条件已全部满足。

建议批准顺序：① 批准 ADR-001/002 → ② 批准本计划 → ③ 登记并批准 P4 测试 → ④ 实现。

---

## ⑦ 人工批准记录

| 项 | 内容 |
|---|---|
| 计划文件 | `docs/plans/P4-selector.md` |
| 提交评审时间 | 2026-10-06 |
| **批准者（具名人类）** | **Shane** |
| 批准时间 | **2026-10-06** |
| 批准结论 | ✅ **APPROVED** |
| 修订次数 | 0 |

> **批准记录**：人类于 2026-10-06 表示"看过了没问题，继续推进"，同时批准 `ADR-001`/`ADR-002`
> 转为 `Accepted`。**No agent may self-approve**（课程 §11.3）——本次批准由人类做出。

## ⑧ 批准后的生效顺序与当前状态

| # | 步骤 | 状态 |
|---|---|---|
| ① | `ADR-001` / `ADR-002` 转为 `Accepted` | ✅ **已完成**（2026-10-06，批准者 Shane） |
| ② | 本执行计划获批 | ✅ **已完成**（2026-10-06，APPROVED） |
| ③ | 登记并批准 P4 的测试（`docs/test-approvals.yaml`） | ⏳ **进行中** —— 门禁 1 要求测试先于实现获批 |
| ④ | 按 §5 步骤 2–8 实现 | ⛔ **未开始**（须待 ③ 完成） |

> **门禁 1 的硬约束**：步骤 ③ 未完成前不得进入步骤 2（创建 `src/selector/__init__.py`）。
> 本条由 `scripts/check_test_approval.py` 在 CI 中强制。
