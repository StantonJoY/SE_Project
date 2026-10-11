"""运行配置的加载与**启动期校验**（REQ-ADS-FR-002 的配置侧 / TD-006）。

Implements: ADR-002 §2 D4（配置属受控面）
            memory-design.md §3 S3（课程配置治理四条规则）
Verifies: REQ-ADS-NFR-COST-001（预算单一来源）、REQ-ADS-NFR-SAFETY-005（阈值单一来源）

课程配置治理四条规则（note 行 1452–1457）在本模块的落地：
  1. 每个环境变量映射到唯一配置键 → `api_key_env` 显式声明（本模块不读环境变量）
  2. **非法值在启动时大声失败（FAIL LOUDLY）** → `validate()` 逐项检查类型/范围
  3. 无环境变量则用默认值 → 缺省字段给默认值
  4. **初始化后不可变** → `AppConfig` 为 frozen dataclass，加载后不可改

`validate()` 覆盖的危险示例（课程行 1461）：`VHIS_DIAMOND_LIMIT=treu`（拼写错误）
被静默当成默认值 —— 本项目用同样的方式拒绝：阈值写错即**启动失败**，不静默取默认。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """配置缺失或非法。**在启动时抛出，不静默降级**（fail loudly）。"""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    timeout_sec: float
    model: str = ""
    api_key_env: str = "LLM_API_KEY"


@dataclass(frozen=True)
class SelectorConfig:
    confidence_threshold: float
    max_retries: int
    context_budget_tokens: int = 2000


@dataclass(frozen=True)
class AuditConfig:
    log_path: str


@dataclass(frozen=True)
class DataConfig:
    ads_path: str
    banned_words_path: str
    scene_rules_path: str


@dataclass(frozen=True)
class EvalConfig:
    """评估门配置（ADR-003 D4：阈值的**单点来源**）。

    阈值**不在代码里硬编码** —— 改评估严格度只改 `config.yaml`；
    非法值由 `AppConfig.validate()` 在启动时**大声拒绝**，不静默取默认值。
    """

    cases_path: str = "eval/eval_cases.json"
    reports_dir: str = "eval/reports"
    pass_rate_threshold: float = 0.95
    latency_p95_threshold_sec: float = 5.0


@dataclass(frozen=True)
class AppConfig:
    """不可变运行配置（规则 4：初始化后不可变）。"""

    llm: LLMConfig
    selector: SelectorConfig
    audit: AuditConfig
    data: DataConfig
    eval: EvalConfig = EvalConfig()
    source_path: str = ""

    # ---- 加载 ----

    @classmethod
    def load(cls, path: str | Path) -> AppConfig:
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"配置文件不存在: {p}")
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ConfigError(f"配置文件不是合法 YAML: {p} ({e})") from e
        if not isinstance(raw, dict):
            raise ConfigError(f"配置文件顶层必须是映射: {p}")

        cfg = cls._from_mapping(raw, source=str(p))
        cfg.validate()
        return cfg

    @classmethod
    def _from_mapping(cls, raw: dict[str, Any], *, source: str = "") -> AppConfig:
        llm = raw.get("llm") or {}
        sel = raw.get("selector") or {}
        aud = raw.get("audit") or {}
        dat = raw.get("data") or {}
        ev = raw.get("eval") or {}
        return cls(
            llm=LLMConfig(
                provider=str(llm.get("provider", "mock")),
                timeout_sec=float(llm.get("timeout_sec", 30)),
                model=str(llm.get("model", "")),
                api_key_env=str(llm.get("api_key_env", "LLM_API_KEY")),
            ),
            selector=SelectorConfig(
                confidence_threshold=float(sel.get("confidence_threshold", 0.5)),
                max_retries=int(sel.get("max_retries", 1)),
                context_budget_tokens=int(sel.get("context_budget_tokens", 2000)),
            ),
            audit=AuditConfig(log_path=str(aud.get("log_path", "logs/audit.jsonl"))),
            data=DataConfig(
                ads_path=str(dat.get("ads_path", "data/ads.json")),
                banned_words_path=str(dat.get("banned_words_path", "data/banned_words.json")),
                scene_rules_path=str(dat.get("scene_rules_path", "data/scene_rules.json")),
            ),
            eval=EvalConfig(
                cases_path=str(ev.get("cases_path", "eval/eval_cases.json")),
                reports_dir=str(ev.get("reports_dir", "eval/reports")),
                pass_rate_threshold=float(ev.get("pass_rate_threshold", 0.95)),
                latency_p95_threshold_sec=float(ev.get("latency_p95_threshold_sec", 5.0)),
            ),
            source_path=source,
        )

    # ---- 启动期校验（FAIL LOUDLY） ----

    def validate(self) -> None:
        """逐项校验；任一非法即抛 `ConfigError`（**不静默取默认值**）。"""
        errors: list[str] = []

        if self.llm.provider not in {"mock", "openai_compatible"}:
            errors.append(
                f"llm.provider={self.llm.provider!r} 非法（应为 mock | openai_compatible）"
            )
        if not (self.llm.timeout_sec > 0):
            errors.append(f"llm.timeout_sec={self.llm.timeout_sec} 必须为正数")
        if self.llm.provider == "openai_compatible" and not self.llm.model:
            errors.append("llm.provider=openai_compatible 时 llm.model 不得为空")

        if not (0.0 <= self.selector.confidence_threshold <= 1.0):
            errors.append(
                f"selector.confidence_threshold={self.selector.confidence_threshold} "
                "必须落在 [0,1]"
            )
        if self.selector.max_retries < 0:
            errors.append(f"selector.max_retries={self.selector.max_retries} 不得为负")
        if self.selector.context_budget_tokens <= 0:
            errors.append(
                f"selector.context_budget_tokens={self.selector.context_budget_tokens} 必须为正"
            )

        if not self.audit.log_path:
            errors.append("audit.log_path 不得为空")

        for label, path in (
            ("data.ads_path", self.data.ads_path),
            ("data.banned_words_path", self.data.banned_words_path),
            ("data.scene_rules_path", self.data.scene_rules_path),
            ("eval.cases_path", self.eval.cases_path),
            ("eval.reports_dir", self.eval.reports_dir),
        ):
            if not path:
                errors.append(f"{label} 不得为空")

        # ---- 评估门阈值（ADR-003 D4：单点来源，非法即拒绝） ----
        if not (0.0 < self.eval.pass_rate_threshold <= 1.0):
            errors.append(
                f"eval.pass_rate_threshold={self.eval.pass_rate_threshold} 必须落在 (0,1]"
            )
        if not (self.eval.latency_p95_threshold_sec > 0):
            errors.append(
                f"eval.latency_p95_threshold_sec={self.eval.latency_p95_threshold_sec} 必须为正数"
            )

        if errors:
            raise ConfigError(
                "配置校验失败（fail loudly，不静默取默认值）：\n  - " + "\n  - ".join(errors)
            )
