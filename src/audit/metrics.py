"""运行时 monitor 登记册（来源：docs/architecture/trace-matrix.md §1 的 Runtime Monitor 列）。

Implements: trace-matrix §1（每条需求都有**具体可度量**的运行时 monitor）
            ADR-002 §9 可观测性要求（监控项具体可度量，非"已加日志"）
Verifies: REQ-ADS-NFR-QA-002（不变量须可验证）、TD-001（22 条 monitor 落地）

**本模块的作用**：把追踪矩阵中声明的 monitor 变成**代码里的单一来源**，
使"声明了哪些指标"与"代码实际暴露哪些指标"不会漂移。

⚠️ **诚实说明**：本模块当前只提供**登记册与快照容器**。
指标的**采集与告警接线**（如 `compliance_escape_count` 的实际计数与 > 0 告警）
属运行时集成，需在 P5 之后随各模块的实际调用点逐步接入 ——
在此之前，追踪矩阵里声明的 monitor 仍是"已定义、未采集"（见 `TD-001`）。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricDefinition:
    """一个运行时 monitor 的定义。"""

    name: str
    requirement: str
    invariant: str
    threshold: float | int
    direction: str  # at_most / at_least / exactly
    description: str

    def is_ok(self, value: float) -> bool:
        """判定某观测值是否满足该 monitor 的阈值。"""
        if self.direction == "at_most":
            return value <= self.threshold
        if self.direction == "at_least":
            return value >= self.threshold
        if self.direction == "exactly":
            return value == self.threshold
        raise ValueError(f"未知 direction: {self.direction!r}")


METRIC_REGISTRY: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        "compliance_escape_count", "REQ-ADS-NFR-SAFETY-001", "INV-ADS-001",
        0, "exactly", "合规逃逸数；> 0 立即重开 ADR-001 T1（最重要的 monitor）",
    ),
    MetricDefinition(
        "out_of_candidate_selection_count", "REQ-ADS-ARCH-002", "INV-ADS-002",
        0, "exactly", "LLM 选择候选集外广告的次数；必须恒为 0",
    ),
    MetricDefinition(
        "llm_output_parse_failure_rate", "REQ-ADS-ARCH-003", "INV-ADS-003",
        0.05, "at_most", "LLM 输出解析失败率；> 5% 触发 RP-004 升级",
    ),
    MetricDefinition(
        "deterministic_replay_diff_count", "REQ-ADS-ARCH-004", "INV-ADS-003",
        0, "exactly", "固定输入重复运行的结果差异处数",
    ),
    MetricDefinition(
        "banned_word_hit_count", "REQ-ADS-NFR-SAFETY-003", "INV-ADS-007",
        0, "at_least", "违禁词命中计数（按命中词分桶，用于词表迭代）",
    ),
    MetricDefinition(
        "scene_violation_reject_count", "REQ-ADS-NFR-SAFETY-004", "INV-ADS-008",
        0, "at_least", "场景约束拒绝计数；双层应各自独立计数",
    ),
    MetricDefinition(
        "low_confidence_degrade_rate", "REQ-ADS-NFR-SAFETY-005", "INV-ADS-006",
        0.5, "at_most", "低置信度降级率；异常升高说明阈值过紧",
    ),
    MetricDefinition(
        "injection_detected_count", "REQ-ADS-SEC-001", "INV-ADS-005",
        0, "at_least", "注入检出计数；任一次检出即触发 prompt 复核",
    ),
    MetricDefinition(
        "e2e_recommend_latency_p95", "REQ-ADS-NFR-PERF-001", "INV-ADS-013",
        5, "at_most", "端到端 p95 延迟（秒）；超阈触发 SLA drift alert",
    ),
    MetricDefinition(
        "llm_context_tokens_per_request", "REQ-ADS-NFR-COST-001", "INV-ADS-014",
        2000, "at_most", "单次请求上下文 token 数",
    ),
    MetricDefinition(
        "post_compaction_constraint_present", "REQ-ADS-NFR-COST-001", "INV-ADS-014",
        1, "exactly", "压缩后 standing constraints 是否仍在 prompt 中（1=在）",
    ),
    MetricDefinition(
        "audit_entries_per_request", "REQ-ADS-GOV-001", "INV-ADS-012",
        1, "exactly", "每次请求的审计记录条数；必须精确等于 1",
    ),
    MetricDefinition(
        "audit_write_failure_count", "REQ-ADS-GOV-001", "INV-ADS-012",
        0, "exactly", "审计写入失败次数；> 0 即整体失败并告警",
    ),
    MetricDefinition(
        "safety_critical_unrecorded_change_count", "REQ-ADS-GOV-002", "INV-ADS-010",
        0, "exactly", "安全关键路径的未记录变更数",
    ),
    MetricDefinition(
        "permission_bypass_count", "REQ-ADS-GOV-002", "INV-ADS-010",
        0, "exactly", "权限绕过事件数；> 0 立即重开 ADR-002 T-6",
    ),
    MetricDefinition(
        "decisions_missing_version_provenance", "REQ-ADS-AI-002", "INV-ADS-012",
        0, "exactly", "缺少 model/prompt/threshold 版本溯源的决策数",
    ),
    MetricDefinition(
        "explanation_decision_isolation_violations", "REQ-ADS-AI-001", "INV-ADS-004",
        0, "exactly", "解释影响决策的次数；必须恒为 0",
    ),
    MetricDefinition(
        "eval_pass_rate", "REQ-ADS-NFR-QA-001", "INV-ADS-016",
        1.0, "at_least", "固定评估集 replay 通过率",
    ),
    MetricDefinition(
        "eval_case_count", "REQ-ADS-NFR-QA-001", "INV-ADS-016",
        20, "at_least", "评估集用例数",
    ),
    MetricDefinition(
        "fit_criterion_test_coverage", "REQ-ADS-NFR-QA-002", "INV-ADS-011",
        1.0, "exactly", "fit criterion 的测试覆盖比例",
    ),
    MetricDefinition(
        "invariant_failing_test_coverage", "REQ-ADS-NFR-QA-002", "INV-ADS-011",
        1.0, "exactly", "不变量具备「会失败」测试的比例",
    ),
    MetricDefinition(
        "no_ad_count", "REQ-ADS-FR-003", "INV-ADS-013",
        0, "at_least", "降级为 no_ad 的计数（按原因码分桶）",
    ),
)


def metric_names() -> tuple[str, ...]:
    """全部已登记的 monitor 名称（供测试与 CI 核对）。"""
    return tuple(m.name for m in METRIC_REGISTRY)


@dataclass
class MetricSnapshot:
    """一次运行期间的指标快照（内存；供写入审计记录的 `monitors` 字段）。"""

    values: dict[str, float] = field(default_factory=dict)

    def record(self, name: str, value: float) -> None:
        if name not in metric_names():
            raise KeyError(f"未登记的 monitor: {name!r}（须先加入 METRIC_REGISTRY）")
        self.values[name] = value

    def increment(self, name: str, delta: float = 1) -> None:
        self.record(name, self.values.get(name, 0) + delta)

    def violations(self) -> list[str]:
        """返回不满足阈值的 monitor 描述（空 = 全部合规）。"""
        out: list[str] = []
        for m in METRIC_REGISTRY:
            if m.name in self.values and not m.is_ok(self.values[m.name]):
                out.append(
                    f"{m.name}={self.values[m.name]} 违反 {m.direction} {m.threshold}"
                    f"（{m.invariant}）"
                )
        return out
