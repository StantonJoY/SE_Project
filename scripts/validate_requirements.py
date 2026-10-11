#!/usr/bin/env python3
"""需求注册表校验器（D1 / 课程门禁第 3 条：Schema gate）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\validate_requirements.py

三层校验：
  1. docs/req/requirements.yaml 符合 docs/req/req-schema.json；
  2. Schema 表达不了的跨条目一致性（唯一性、来源引用、版本合法性、
     MoSCoW/status 自洽、非功能 metric 完整性、待决项覆盖）；
  3. **架构输入双向一致性**：注册表中的 asr_id / invariants 必须真实存在于
     docs/architecture/asr-register.md 与 docs/architecture/invariants.md；
     反向，登记册中引用的 REQ ID 也必须存在于注册表。

退出码：0 = 通过；1 = 校验失败。本脚本只读，不修改任何文件。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    print("缺少 PyYAML：pip install PyYAML", file=sys.stderr)
    raise SystemExit(1) from None

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover
    print("缺少 jsonschema：pip install jsonschema", file=sys.stderr)
    raise SystemExit(1) from None

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "req" / "requirements.yaml"
SCHEMA_PATH = ROOT / "docs" / "req" / "req-schema.json"

NON_FUNCTIONAL = {"quality", "performance", "cost"}
AUTOMATED = {
    "unit_test", "negative_test", "property_test", "schema_validation",
    "deterministic_replay", "evaluation_replay", "static_analysis",
    "ci_gate", "metric_measurement",
}
# 非 fail-closed 的降级措辞：课程行 1713（retry 是 fail-open）
FAIL_OPEN_PHRASES = ("fix the bug", "fix bug", "修复 bug", "修复缺陷", "retry", "重试或修复")

# 只认行内代码 `ASR-...` / `INV-...`，从而忽略模板占位（如 `INV-ADS-NNN`）与正文散文。
# 要求至少一个数字，避免把带 NNN/xxx 的占位符当成真实 ID。
ASR_ID_RE = re.compile(r"`(ASR-[A-Z0-9-]*[0-9]+)`")
INV_ID_RE = re.compile(r"`(INV-[A-Z0-9-]*[0-9]+)`")


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path):
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def all_requirements(registry: dict) -> list[dict]:
    return list(registry.get("baseline_requirements") or []) + list(
        registry.get("candidate_requirements") or []
    )


def declared_asr_ids(req: dict) -> set[str]:
    """一条需求可强制多个 ASR：asr_id 为主条目，asr_ids 为全部条目。"""
    ids: set[str] = set()
    if req.get("asr_id"):
        ids.add(req["asr_id"])
    ids.update(req.get("asr_ids") or [])
    return ids


# --------------------------------------------------------------------------
# 第 1 层：JSON Schema
# --------------------------------------------------------------------------

def check_schema(registry: dict, schema: dict) -> list[str]:
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(registry), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"[schema] {where}: {err.message}")
    return errors


# --------------------------------------------------------------------------
# 第 2 层：跨条目一致性
# --------------------------------------------------------------------------

def check_consistency(registry: dict) -> list[str]:
    errors: list[str] = []
    reqs = all_requirements(registry)
    baseline = registry.get("baseline_requirements") or []
    candidate = registry.get("candidate_requirements") or []

    ids = [r.get("id") for r in reqs]

    # --- ID 唯一 ---
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        errors.append(f"[consistency] requirements: REQ ID 重复 {dupes}")

    # --- 语义化 ID：类别前缀必须与 type 相容 ---
    type_family = {
        "functional": ("FR",),
        "invariant": ("ARCH", "NFR-SAFETY"),
        "security": ("SEC",),
        "governance": ("GOV", "AI"),
        "performance": ("NFR-PERF",),
        "cost": ("NFR-COST",),
        "quality": ("NFR-QA", "AI"),
    }
    for r in reqs:
        rid, rtype = r.get("id", ""), r.get("type")
        body = rid.replace("REQ-ADS-", "").replace("REQ-", "")
        families = type_family.get(rtype, ())
        if families and not any(body.startswith(f + "-") for f in families):
            errors.append(
                f"[consistency] {rid}: ID 类别前缀与 type={rtype} 不相容（期望 {families}）"
            )

    # --- 基线版本一致；候选必须声明 deferred_to_round ---
    baseline_version = registry.get("project", {}).get("baseline_version")
    for r in baseline:
        if r.get("version") != baseline_version:
            errors.append(
                f"[consistency] {r.get('id')}: 基线需求 version={r.get('version')!r} "
                f"须等于 project.baseline_version={baseline_version!r}"
            )
        if r.get("priority") == "must" and r.get("status") == "deferred":
            errors.append(f"[consistency] {r.get('id')}: 基线需求不得为 deferred 状态")
    for r in candidate:
        if not r.get("deferred_to_round"):
            errors.append(f"[consistency] {r.get('id')}: 候选需求必须声明 deferred_to_round")

    # --- legacy_id：旧编号唯一且与新编号一一对应 ---
    legacy = [r.get("legacy_id") for r in reqs if r.get("legacy_id")]
    if len(legacy) != len(set(legacy)):
        errors.append(f"[consistency] legacy_id: 旧编号被重复映射 {sorted(legacy)}")
    lmap = registry.get("legacy_id_map") or {}
    for old, new in lmap.items():
        if new not in set(ids):
            errors.append(f"[consistency] legacy_id_map: {old} 指向不存在的 {new}")
    for r in reqs:
        lid = r.get("legacy_id")
        if lid and lmap.get(lid) != r.get("id"):
            errors.append(
                f"[consistency] {r.get('id')}: legacy_id {lid} 与 legacy_id_map 不一致"
            )

    # --- source_refs 引用完整性 ---
    declared = {s.get("key"): s for s in registry.get("sources", []) if isinstance(s, dict)}
    scope_out = registry.get("scope", {}).get("out", [])
    for r in reqs:
        for ref in r.get("source_refs", []):
            if ref.get("source") not in declared:
                errors.append(
                    f"[consistency] {r.get('id')}: source_refs 引用未声明的 source key {ref.get('source')!r}"
                )
    for entry in scope_out:
        for ref in entry.get("source_refs") or []:
            if ref.get("source") not in declared:
                errors.append(
                    f"[consistency] scope.out {entry.get('item')!r}: 引用未声明的 source key {ref.get('source')!r}"
                )

    # --- 死来源检测 ---
    used = {ref.get("source") for r in reqs for ref in r.get("source_refs", [])}
    used |= {ref.get("source") for e in scope_out for ref in (e.get("source_refs") or [])}
    for key in declared:
        if key not in used:
            errors.append(f"[consistency] sources: 来源 {key!r} 未被任何需求或范围决策引用")

    # --- 非功能需求 metric 合理性；禁止仅 code_review ---
    for r in reqs:
        if r.get("type") in NON_FUNCTIONAL:
            metric = r.get("metric")
            if isinstance(metric, dict) and not isinstance(metric.get("threshold"), (int, float)):
                errors.append(f"[consistency] {r.get('id')}: metric.threshold 必须是数值")
        if set(r.get("verification", [])) == {"code_review"}:
            errors.append(
                f"[consistency] {r.get('id')}: 仅有 code_review 不足以验证，需至少一种自动化手段"
            )

    # --- fallback 质量：禁止「修 bug」与非 fail-closed 措辞 ---
    for r in reqs:
        if r.get("type") != "invariant":
            continue
        fb = (r.get("fallback") or "").strip()
        if not fb:
            errors.append(f"[consistency] {r.get('id')}: invariant 必须有可操作的 fallback")
            continue
        low = fb.lower()
        if any(p in low for p in FAIL_OPEN_PHRASES):
            errors.append(
                f"[consistency] {r.get('id')}: fallback 含非 fail-closed 措辞（{fb!r}）——"
                "要么写成具体安全动作，要么在文档中显式说明为何不构成 fail-open"
            )

    # --- status=verified 必须有自动化验证 ---
    for r in reqs:
        if r.get("status") == "verified" and not (set(r.get("verification", [])) & AUTOMATED):
            errors.append(f"[consistency] {r.get('id')}: status=verified 但无任何自动化验证手段")

    # --- 不变式类 ASR 必须形式化进不变量登记册 ---
    # 候选需求推迟到后续轮次，其不变量也在那一轮才确定，不在此处强制。
    # 允许一条需求映射到 0 条自有不变量而由共享不变量覆盖，但必须在
    # invariants.md §7 的覆盖表中说明，因此这里仅在「声明了 asr 却没有
    # 任何不变量、且已存在于基线」时报错。
    for r in baseline:
        if r.get("asr") and r.get("type") == "invariant" and not r.get("invariants"):
            errors.append(
                f"[consistency] {r.get('id')}: 不变式类 ASR 未登记任何 INV 条目"
                "（应在 invariants.md 中形式化，或在 §7 覆盖表中说明由共享不变量覆盖）"
            )

    # --- open_questions 引用必须存在 ---
    idset = set(ids)
    for oq in registry.get("open_questions", []):
        for blocked in oq.get("blocks", []):
            if blocked not in idset:
                errors.append(f"[consistency] {oq.get('id')}: blocks 引用不存在的需求 {blocked!r}")

    # --- evolution_rounds 覆盖全部 target_versions ---
    rounds = {e.get("round") for e in registry.get("evolution_rounds", [])}
    for v in registry.get("project", {}).get("target_versions", []):
        if v not in rounds:
            errors.append(f"[consistency] evolution_rounds: 缺少 target_version {v!r} 的轮次定义")

    return errors


# --------------------------------------------------------------------------
# 第 3 层：架构输入双向一致性（A1 / A2 产物）
# --------------------------------------------------------------------------

def _ids_in_file(path: Path, pattern: re.Pattern) -> set[str]:
    if not path.exists():
        return set()
    return set(pattern.findall(path.read_text(encoding="utf-8")))


def check_architecture_inputs(registry: dict) -> list[str]:
    errors: list[str] = []
    inputs = registry.get("architecture_inputs") or {}
    reqs = all_requirements(registry)
    req_ids = {r.get("id") for r in reqs}

    asr_path = ROOT / inputs.get("asr_register", "")
    inv_path = ROOT / inputs.get("invariant_register", "")

    for label, path in (("asr-register", asr_path), ("invariant-register", inv_path)):
        if not path.exists():
            errors.append(f"[architecture] {label} 文件不存在: {path.relative_to(ROOT)}")
            return errors

    known_asr = _ids_in_file(asr_path, ASR_ID_RE)
    known_inv = _ids_in_file(inv_path, INV_ID_RE)

    # 正向：注册表引用的 ASR / INV 必须存在
    for r in reqs:
        for asr_id in declared_asr_ids(r):
            if asr_id not in known_asr:
                errors.append(
                    f"[architecture] {r.get('id')}: asr_id {asr_id!r} 在 {asr_path.name} 中不存在"
                )
        for inv in r.get("invariants", []):
            if inv not in known_inv:
                errors.append(
                    f"[architecture] {r.get('id')}: 引用的 {inv!r} 在 {inv_path.name} 中不存在"
                )

    # 反向：登记册引用的 REQ ID 必须存在，且回指一致
    declared_asr = {a for r in reqs for a in declared_asr_ids(r)}
    for asr_id in sorted(known_asr - declared_asr):
        errors.append(f"[architecture] {asr_path.name}: {asr_id} 未被任何需求引用（孤儿 ASR）")

    declared_inv = {i for r in reqs for i in r.get("invariants", [])}
    for inv in sorted(known_inv - declared_inv):
        errors.append(f"[architecture] {inv_path.name}: {inv} 未被任何需求引用（孤儿不变量）")

    # 登记册中形如 REQ-... 的引用必须是真实需求
    for label, path in (("asr-register", asr_path), ("invariant-register", inv_path)):
        text = path.read_text(encoding="utf-8")
        refs = set(re.findall(r"`(REQ-[A-Z0-9-]+)`", text))
        for ref in sorted(refs - req_ids):
            errors.append(f"[architecture] {label}: 引用了不存在的需求 {ref!r}")

    return errors


# --------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    registry_path = Path(argv[1]) if len(argv) > 1 else REGISTRY_PATH
    schema_path = Path(argv[2]) if len(argv) > 2 else SCHEMA_PATH

    for path in (registry_path, schema_path):
        if not path.exists():
            print(f"找不到文件: {path}", file=sys.stderr)
            return 1

    registry = load_yaml(registry_path)
    schema = load_json(schema_path)

    if not isinstance(registry, dict):
        print(f"注册表顶层必须是对象: {registry_path}", file=sys.stderr)
        return 1

    errors = (
        check_schema(registry, schema)
        + check_consistency(registry)
        + check_architecture_inputs(registry)
    )

    if errors:
        print(f"FAIL — {registry_path.name} 未通过校验，共 {len(errors)} 个问题：")
        for e in errors:
            print(f"  - {e}")
        return 1

    baseline = registry.get("baseline_requirements", [])
    candidate = registry.get("candidate_requirements", [])
    n_asr = sum(1 for r in baseline if r.get("asr"))
    n_inv = sum(1 for r in baseline if r.get("type") == "invariant")
    n_nfr = sum(1 for r in baseline if r.get("type") in NON_FUNCTIONAL)
    by_status: dict[str, int] = {}
    for r in baseline:
        by_status[r.get("status")] = by_status.get(r.get("status"), 0) + 1

    print(
        f"PASS — {registry_path.name} 通过 Schema、一致性与架构输入校验\n"
        f"  基线需求 {len(baseline)} 条（ASR {n_asr}，不变式 {n_inv}，非功能 {n_nfr}）\n"
        f"  候选需求 {len(candidate)} 条（归属后续轮次，未并入基线）\n"
        f"  来源 {len(registry.get('sources', []))} 个，待决项 {len(registry.get('open_questions', []))} 个\n"
        f"  基线状态分布: " + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items()))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
