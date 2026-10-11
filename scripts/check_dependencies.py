#!/usr/bin/env python3
"""依赖检查（D7 门禁 2 的 "dependency checks" 部分）。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe scripts\\check_dependencies.py

检查四件事：
  ① `pyproject.toml` 中声明的运行时依赖，必须被 `src/` 实际 import（否则是声明臃肿）；
  ② `src/` 中 import 的**第三方**模块，必须在 `pyproject.toml` 中声明（否则是隐藏依赖）；
  ③ dev 依赖同理（作用域为 `test/` 与 `scripts/`）；
  ④ 本地包（ads/scene/compliance/...）不得被当作第三方写入依赖声明。

③ 的意义：课程把 "hallucinated dependencies"（幻觉依赖）列为 AI 时代技术债之一。
本检查使"依赖声明与代码实际使用不一致"无法静默存在。

退出码：0 = 通过；1 = 有问题。本脚本只读。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"

# 标准库模块名集合
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# PyPI 分发名 → import 名 的映射（仅需覆盖本项目用到的；分发名与模块名不同者）
DIST_TO_IMPORT = {
    "pyyaml": "yaml",
    "types_jsonschema": "jsonschema",  # 仅提供类型存根，不是运行时 import
}

# 仅提供存根（不产生 import）的分发名 —— 不应参与"声明必须被使用"的检查
STUB_ONLY = {"types_jsonschema"}


def declared() -> tuple[set[str], set[str]]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data.get("project", {})

    def normalize(reqs: list[str]) -> set[str]:
        out = set()
        for r in reqs:
            name = r.split("[")[0].split(">=")[0].split("==")[0].split("<")[0].split(";")[0].strip()
            if not name:
                continue
            key = name.lower().replace("-", "_")
            # 若分发名与 import 名不同，按 import 名记录
            key = DIST_TO_IMPORT.get(key, key)
            out.add(key)
        return out

    runtime = normalize(project.get("dependencies") or [])
    dev = normalize((project.get("optional-dependencies") or {}).get("dev") or [])
    return runtime, dev


def depcheck_config() -> tuple[set[str], set[str]]:
    """读取 [tool.depcheck] 的显式豁免（避免规则藏在脚本里）。"""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    cfg = (data.get("tool") or {}).get("depcheck") or {}
    fallbacks = {m.lower().replace("-", "_") for m in (cfg.get("import_fallbacks") or [])}
    known = {m.lower().replace("-", "_") for m in (cfg.get("known_undeclared") or [])}
    return fallbacks, known


def local_packages() -> set[str]:
    """本地模块名 —— 这些不是第三方依赖。

    包含两类：
      · `src/` 下的顶层包（ads / scene / compliance / selector / render / audit / app）
      · **`scripts/` 与 `eval/` 下的兄弟模块**（无 `__init__.py` 的平铺脚本）

    后者是必需的：`test/` 或 `scripts/` 中的一个脚本 import 同目录的另一个脚本
    （如 `test_mutation_check.py` → `mutation_check`）是**合法的一等方依赖**，
    若不剔除会被误报为"未声明的第三方模块"。
    """
    names: set[str] = set()
    src = ROOT / "src"
    names |= {p.name for p in src.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    for extra in ("scripts", "eval"):
        d = ROOT / extra
        if d.is_dir():
            names |= {p.stem for p in d.glob("*.py") if not p.name.startswith("_")}
    return names


def imports_in(paths: list[Path], local: set[str]) -> set[str]:
    """收集第三方顶层模块名（已剔除标准库与本地包）。"""
    found: set[str] = set()
    for p in paths:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # 相对导入，跳过
                    continue
                names = [node.module or ""]
            for n in names:
                top = n.split(".")[0]
                if not top or top in STDLIB or top in local:
                    continue
                found.add(top.lower().replace("-", "_"))
    return found


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    runtime, dev = declared()
    fallbacks, known_undeclared = depcheck_config()
    local = local_packages()

    src_files = sorted((ROOT / "src").rglob("*.py"))
    # scripts/ 下划线前缀为临时脚本（不属于交付物），不纳入依赖判定；
    # 它们的存在本身已在下文以 notes 提示清理。
    aux_files = (
        sorted((ROOT / "test").rglob("*.py"))
        + [p for p in sorted((ROOT / "scripts").rglob("*.py")) if not p.name.startswith("_")]
    )

    src_imports = imports_in(src_files, local)
    aux_imports = imports_in(aux_files, local)

    errors: list[str] = []
    notes: list[str] = []

    # ② src 用的第三方必须声明（可在 runtime 或 dev 中）
    for mod in sorted(src_imports):
        if mod not in runtime and mod not in dev:
            errors.append(f"src/ 使用了第三方模块 {mod!r}，但 pyproject.toml 未声明（隐藏依赖）")

    # ③ test/scripts 用的第三方必须声明（可为 dev）；known_undeclared 为显式登记的债
    for mod in sorted(aux_imports - src_imports):
        if mod in runtime or mod in dev:
            continue
        if mod in known_undeclared:
            notes.append(f"未声明的第三方 {mod!r} 已登记于 [tool.depcheck].known_undeclared（技术债）")
            continue
        errors.append(f"test/ 或 scripts/ 使用了第三方模块 {mod!r}，但 pyproject.toml 未声明")

    # ① 声明的 runtime 依赖必须真的被 src 使用（存根与显式 import 回退除外）
    allowed_unused = STUB_ONLY | fallbacks
    for mod in sorted(runtime):
        if mod in allowed_unused:
            continue
        if mod not in src_imports:
            errors.append(f"pyproject.toml 声明了运行时依赖 {mod!r}，但 src/ 从未 import（声明臃肿）")

    # ④ 本地包不得出现在依赖声明中
    for mod in sorted(local):
        if mod in runtime or mod in dev:
            errors.append(f"本地包 {mod!r} 被写入依赖声明（不得把自身当作第三方依赖）")

    # ⑤ 临时脚本（下划线前缀）不应留在仓库 —— 它们会引入未声明的依赖
    temp_scripts = sorted(p.name for p in (ROOT / "scripts").glob("_*.py"))
    if temp_scripts:
        notes.append(f"临时脚本（应删除，不属于交付物）: {temp_scripts}")

    notes.append(f"运行时依赖 {sorted(runtime)}")
    notes.append(f"dev 依赖 {sorted(dev)}")
    notes.append(f"src/ 第三方 import {sorted(src_imports)}")
    notes.append(f"aux 第三方 import {sorted(aux_imports - src_imports)}")
    notes.append(f"本地包（src/ 顶层）{sorted(local)}")

    for n in notes:
        print(f"  · {n}")

    if errors:
        print()
        print(f"FAIL — 依赖检查未通过，共 {len(errors)} 项：")
        for e in errors:
            print(f"  - {e}")
        return 1

    print()
    print("PASS — 依赖声明与代码实际使用一致（无隐藏依赖、无臃肿声明）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
