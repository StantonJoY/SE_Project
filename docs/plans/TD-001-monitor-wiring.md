# TD-001 补监控方案（运行时 monitor 接线）

> 目标：把「22 条 monitor **已登记**」推进到「**可采集、可聚合、可判红**」。
> 状态：方案待执行 · 日期：2026-11-22 · 预计 2–2.5 小时

> **V2 范围核对（2026-11-22）**：V2 核心交付已合入 `main`，但 `src/app/pipeline_v2.py` 的审计 evidence 尚无 `monitors`，`scripts/report_monitors.py` 尚不存在。因此步骤 5、依赖的分类/聚合器与相应测试仍未实施，TD-001 保持开放。当前 V2 预算、合规与审计测试通过不能证明 monitor 已接线。步骤 1 的 TA-0008 只是拟用编号，执行前须核对当时批准登记册，不构成已获批准。V2 已有证据与本次文档验证见 [交付总结](../testing/V2-Delivery-Summary.md)。

---

## 0. 现状（先量准，再动手）

| 事实 | 证据 |
|---|---|
| 登记了 **22 条** 指标，每条带 `requirement / invariant / threshold / direction` | `src/audit/metrics.py` 的 `METRIC_REGISTRY` |
| 容器与判定已实现：`record()` 会拒绝未登记的名字（防漂移）、`violations()` 用 `is_ok()` 判阈值 | `MetricSnapshot` |
| V1 管道**只填了 2 条**：`llm_context_tokens_per_request`、`post_compaction_constraint_present` | 真实审计记录的 `monitors` 字段 |
| **V2 管道一条都没接**（`pipeline_v2.py` 里没有 `MetricSnapshot`） | `grep` 结果 |
| 没有聚合器：rate / p95 这类指标需要多请求才有意义 | — |
| 没有任何测试保证「登记即采集」 | — |

**一句话**：登记册是完整的，采集是残缺的（2/22），聚合与报警不存在。

---

## 1. 先分类，别急着填（最容易被跳过的一步）

22 条里混着三种东西。全部硬填会产出**永远为 0 的假监控**，比不填更坏。

| 类别 | 判定标准 | 条数（预估） |
|---|---|---|
| `runtime` | 单次请求内可观测 | 11–12 |
| `aggregate` | 需要对一批请求/回放聚合（rate、p95、覆盖率） | 5–6 |
| `static` | 运行时不可观测，由 CI 脚本判定（恒 0 类） | 5 |

| 指标 | 分类 | 采集点 / 判定者 |
|---|---|---|
| `llm_context_tokens_per_request` | runtime（已接） | `selector.context` |
| `post_compaction_constraint_present` | runtime（已接） | `selector.context` |
| `llm_output_parse_failure_rate` | runtime（记 0/1） | `app.pipeline` 解析失败分支 |
| `out_of_candidate_selection_count` | runtime（记 0/1） | `app.pipeline` 解析拒绝分支 |
| `banned_word_hit_count` | runtime（计数） | `compliance` 的 `banned_words` 步 |
| `scene_violation_reject_count` | runtime（0/1） | `compliance` 的 `scene` 步 |
| `injection_detected_count` | runtime（0/1） | `app.sanitize` |
| `no_ad_count` | runtime（0/1） | `app.pipeline` 各降级出口 |
| `audit_entries_per_request` | runtime（恒 1） | 审计写入点 |
| `decisions_missing_version_provenance` | runtime（0/1） | 审计组装前自检 |
| `explanation_decision_isolation_violations` | runtime（0/1） | 解释路径返回后比对 `ad_id` |
| `e2e_recommend_latency_p95` | runtime（ms）→ 聚合 p95 | 管道首尾计时 |
| `low_confidence_degrade_rate` | runtime（0/1）→ 聚合 | 低置信度降级分支 |
| `audit_write_failure_count` | runtime（0/1，仅失败路径可观测） | `AuditWriteError` 分支 |
| `compliance_escape_count` | **aggregate** | 回放重算：对已输出结果再跑一次合规 |
| `deterministic_replay_diff_count` | **aggregate** | `eval_runner` 双跑比对 |
| `eval_pass_rate` / `eval_case_count` | **aggregate** | 三套 `eval_runner` |
| `safety_critical_unrecorded_change_count` | **static** | `check_safety_paths.py` |
| `permission_bypass_count` | **static** | 无运行时权限层，恒 0 由 CI 保证 |
| `fit_criterion_test_coverage` / `invariant_failing_test_coverage` | **static** | `fitness_functions.py` + `mutation_check.py` |

> 分类结果写进 `MetricDefinition.source`，并加一条测试：**任何 `static` 指标一旦出现在审计的 `monitors` 里就 FAIL**（防假数据）。

---

## 2. 执行步骤（8 步，每步都有验收）

### 步骤 1 · 签 TA-0008（改测试前必须）

- 覆盖文件：`test/offline/test_monitors.py`（新建）
- `req_ids`：`REQ-ADS-NFR-QA-002`、`REQ-ADS-GOV-001`
- `approved_at` 必须早于实现提交（流程照 `TA-0005`）
- **产出**：`docs/test-approvals.yaml` 新增记录
- **验收**：`check_test_approval --files test/offline/test_monitors.py` 通过

### 步骤 2 · 先写测试（此时必须是红的）

新建 `test/offline/test_monitors.py`，4 条：

| 测试 | 断言 |
|---|---|
| `test_runtime_metrics_are_all_emitted` | 跑三类场景（正常 ad / 合规拒绝 / 注入拦截），三次审计的 `monitors` 键**并集**覆盖全部 `source=="runtime"` 指标 |
| `test_static_metrics_never_emitted` | 审计里不得出现 `source=="static"` 的指标名 |
| `test_rate_metrics_are_fractions` | `*_rate` 类只允许 0/1 或 0..1 区间，不得出现 0–100 |
| `test_report_monitors_flags_violation` | 用合成 JSONL（含一次合规逃逸）驱动聚合器 → 退出码 1 且输出含指标名 |

- **验收**：`pytest test/offline/test_monitors.py` **4 failed**（因为实现未写）

### 步骤 3 · `metrics.py` 加 `source` 字段与分类

- `MetricDefinition` 增 `source: str`（`runtime|aggregate|static`），22 条逐个填
- `metric_names(source=None)` 支持过滤
- `MetricSnapshot.record()` 增校验：`static` 指标禁止 record（抛 `KeyError`）
- **验收**：`pytest test/offline/test_monitors.py::test_static_metrics_never_emitted` 由红转绿

### 步骤 4 · V1 管道填 11 条 runtime 值

改动点全部在 `src/app/pipeline.py` 已有的分支上（**不改决策逻辑**）：

| 位置 | 记录 |
|---|---|
| 入口计时开始 | —（仅起 `time.perf_counter()`） |
| sanitize 后 | `injection_detected_count` |
| 解析失败分支 | `llm_output_parse_failure_rate=1` |
| 解析选中集外 | `out_of_candidate_selection_count=1` |
| 合规后 | `banned_word_hit_count`、`scene_violation_reject_count` |
| 低置信度降级 | `low_confidence_degrade_rate=1` |
| 解释返回后 | `explanation_decision_isolation_violations`（比对 `ad_id` 是否被改写） |
| 审计组装前 | `decisions_missing_version_provenance`（provenance 三字段齐全为 0） |
| 写审计 | `audit_entries_per_request=1`；失败路径 `audit_write_failure_count=1` |
| 所有出口 | `no_ad_count`（ad=0 / no_ad=1） |
| 返回前 | `e2e_recommend_latency_p95`（ms） |

- **验收**：`test_runtime_metrics_are_all_emitted` 转绿；审计记录里 `monitors` 从 2 个键变成 11+ 个

### 步骤 5 · V2 管道接同一套（子集）

`pipeline_v2.py` 目前**完全没有** monitores。最小接入：

- `llm_output_parse_failure_rate`、`no_ad_count`、`e2e_recommend_latency_p95`、`audit_entries_per_request`
- 写进 `evidence["monitors"]`，随 `ledger.finalize()` 落库（`audit.record_json`）

- **验收**：V2 审计 JSON 里出现 `monitors` 键；既有 V2 测试不回归

### 步骤 6 · 新增 `scripts/report_monitors.py`（聚合 + 判红）

```bash
python scripts/report_monitors.py --audit logs/audit.jsonl   # V1
python scripts/report_monitors.py --sqlite logs/bidding-v3.sqlite3  # V2
```

- 读审计 → 按 `source` 分组 → 求和/求率/求 p95
- 逐条 `is_ok()`，输出：

```
指标                                值      阈值        结论
compliance_escape_count            0      == 0        OK
llm_output_parse_failure_rate      0.02   <= 0.05     OK
e2e_recommend_latency_p95          312ms  <= 5000ms   OK
...
判定：通过（0 项违规）        # 有违规则列出并 exit 1
```

- `static` 类不参与计算，打印一行指向对应检查器
- **验收**：`test_report_monitors_flags_violation` 转绿；对真实日志跑一次得 `0 项违规`

### 步骤 7 · 文档与债务

| 文件 | 改动 |
|---|---|
| `docs/architecture/trace-matrix.md` | monitor 列标注采集方式（运行/聚合/静态） |
| `docs/debt-register.md` | `TD-001` 关闭，写「处置：22 条中 11 runtime + 5 aggregate + 6 static」 |
| `docs/HANDOVER-V3.md` | §6 数字表补一行「monitor 覆盖率」；§7 弱点里删掉 TD-001 |
| `docs/ai-use-log.yaml` | 追加一条 entry |

### 步骤 8 · 全量验证

```bash
pytest test/offline -q                 # 预期 683 左右，全绿
python scripts/mutation_check.py       # 33/33
python scripts/report_monitors.py --audit logs/audit.jsonl   # 0 违规
# 其余 6 道门禁
```

---

## 3. 完成判据（DoD）

1. `monitors` 字段在真实审计里出现 **≥11 个**键（V1）与 **≥4 个**键（V2）；
2. `report_monitors.py` 对真实日志输出"0 项违规"，且对合成逃逸能 exit 1；
3. 全部 22 条指标在 `METRIC_REGISTRY` 里有明确 `source`，无"未分类"；
4. `TD-001` 关闭，且关闭理由写的是**分类与覆盖率**，不是"已加日志"；
5. 679+ 测试全绿、变异 33/33、7 道门禁全 PASS。

---

## 4. 风险与前置确认

| 风险 | 处理 |
|---|---|
| **假监控**：把恒 0 的指标硬填 0 | 用 `source=static` 禁止 record，加测试锁定 |
| **rate 口径混乱**：0/1 与 0.05 混算 | 测试限定 `*_rate` 只能是分数（0..1） |
| **V2 审计结构不同**：V2 的 `audit.record_json` 是 JSON blob | 先确认 `evidence` 能带 `monitors` 且不违反 ledger 的 schema 校验 |
| **延迟统计**：p95 需要样本量 | 少于 20 条时输出 `n<20`，不给 p95（避免用 2 个样本算分位数） |
| **改测试触发门禁 1** | 先签 TA-0008，再提交测试，最后提交实现 |
| **`compliance_escape_count` 不可能自证** | 明确它是 aggregate：由回放重算，而非管道自报 |

---

## 5. 明确不做

- 不接真实告警通道（邮件/Slack）：本项目无部署环境，`exit 1` 即"报警"；
- 不引入 metrics 库（prometheus/statsd）：零新依赖是硬约束；
- 不做可视化面板：`report_monitors.py` 的表格输出即交付物。
