# 执行计划清单（Execution Plan Manifest）— 模板

> **用途**：课程要求编码 agent **在写任何代码之前**先产出此清单，并**停下来等人工批准**。
> 被 `Prompt.md`（D9 启动指令）引用，由 `AGENTS.md` §⑥ 的验证要求约束。
>
> **MANDATE（课程 §9.4）**：
> **在 Execution Plan Manifest 获得明确批准之前，严格禁止输出源代码、修改文件或调用执行类工具。**
>
> **计划就是契约**（课程 §9.4）：一旦批准，Build 就承诺于所声明的**文件、导入与接口**；
> 需要变更的修改必须**重新产出经批准的计划**。若校验失败，计划被拒绝，
> Build agent 必须**修订计划，不得跳到代码**。

---

## 使用方法

1. 复制本模板 → `docs/plans/<TASK-ID>-<slug>.md`（例如 `docs/plans/P4-selector.md`）
2. 填写五个部分（下表）
3. **提交人工评审，停止输出**
4. 获批后方可开始实现；实现过程中若需偏离计划，**回到第 2 步重新出计划**

| # | 部分 | 防止什么 | 由谁校验 |
|---|---|---|---|
| ① | **Traceability**（可追溯性） | 范围蔓延——构建规格中不存在的东西 | Human + Plan agent |
| ② | **Interface Contract**（接口契约） | 错误的类／方法签名 | AST checker（Tier 1） |
| ③ | **Scope Boundaries**（范围边界） | 违禁导入与沙箱逃逸 | Sandbox verifier |
| ④ | **Testing Strategy**（测试策略） | 测试验证错误的标准 | Tester agent 交叉引用 |
| ⑤ | **Implementation Steps**（实施步骤） | 步骤缺失与隐藏假设 | Human + ordering verifier |

---

## ① Traceability

```yaml
task_id: "<TASK-ID>"
title: "<一句话说明本次要构建什么>"
requirements: ["REQ-ADS-XXX-NNN", ...]        # 必须存在于 docs/req/requirements.yaml
invariants: ["INV-ADS-NNN", ...]              # 必须存在于 docs/architecture/invariants.md
asrs: ["ASR-ADS-NN", ...]                     # 必须存在于 docs/architecture/asr-register.md
fit_criteria:
  - id: "FC-<TASK-ID>-01"
    condition: "<可机器检查的条件，须来自 requirements.yaml 的 fit_criterion>"
test_design: "<测试方式，例如 pytest + MockLLM（离线确定性）>"
```

**自检**：每个 `REQ`／`INV`／`ASR` ID 都必须**真实存在**（不是编造的）。
`scripts/validate_requirements.py` 会校验注册表与两个登记册的**双向一致性**——
若计划引用了不存在的 ID，该检查即会失败。

## ② Interface Contract

```yaml
elements:
  - file: "src/<pkg>/<module>.py"
    class: "<ClassName>"            # 或 function
    implements: "<Protocol/ABC，若有>"
    public_methods:
      - name: "<method>"
        params: {<name>: <type>, ...}
        returns: "<type>"
        raises: ["<ErrorType>", ...]
```

**自检**：签名必须与 `AGENTS.md` ④ 的模块组织表、⑤ 的集成契约表一致。

## ③ Scope Boundaries

```yaml
target_files: ["src/<pkg>/<module>.py", ...]   # **只允许**创建/修改这些文件
allowed_imports: ["<pkg>", "<stdlib>", ...]
prohibited_imports: ["os", "subprocess", "requests", ...]   # 显式列出，不是"默认禁止"
data_access: "<读写哪些数据文件；candidates 来自何处>"
frozen_paths_not_touched:                       # 必须与 AGENTS.md ③ 一致
  - "src/ads/"
  - "src/scene/"
  - "src/compliance/"
  - "data/"
```

> **注意**：`src/compliance/`、`src/ads/schema.py`、`data/*.json`、`docs/req/requirements.yaml`
> 属**须 ADR** 的安全关键路径（清单由 `scripts/check_safety_paths.py --show-paths` 输出）。
> 计划若触及这些路径，**必须同时产出或引用 ADR**，否则 CI 阻断。

## ④ Testing Strategy

```yaml
cases:
  - name: "<test_function_name>"
    fit_criterion: "FC-<TASK-ID>-01"
    type: "unit | property_based | negative | deterministic_replay"
    mock: "<MockLLM / 无>"
    invariant_covered: "INV-ADS-NNN"     # 若为不变量，须有**会失败**的反例测试
```

**硬性要求**（`docs/code-governance/verification-constraints.md`）：

- 每条 fit criterion ≥ 1 个测试（V1）
- **每条不变量 ≥ 1 个「会失败」的反例测试**（V2）
- 测试 docstring **引用它验证的 REQ/INV ID**（V3）
- **不得使用 pytest `tmp_path`**（受限沙箱兼容；用 I/O 边界打桩替代）
- 未覆盖项必须在 `docs/code-governance/acceptance-coverage-map.yaml` 登记去向与阻塞原因

## ⑤ Implementation Steps

```yaml
steps:
  - "1. <具体动作，含目标文件>"
  - "2. ..."
verification_after_each_step: "<每步如何自验，例如 pytest test/offline -q>"
rollback: "<若中途失败如何回到干净状态>"
```

**自检**：步骤必须是**有顺序依赖的**具体动作，不是"实现功能 X"这类模糊表述。

---

## 人工批准记录

| 项 | 内容 |
|---|---|
| 计划文件 | `docs/plans/<TASK-ID>-<slug>.md` |
| 提交评审时间 | ⏳ |
| **批准者（具名人类）** | ⏳ |
| 批准时间 | ⏳ |
| 批准结论 | `APPROVED` / `CHANGES REQUIRED` / `REJECTED` |
| 修订次数 | ⏳ |

> **No agent may self-approve**（课程 §11.3）。批准者必须是具名人类。
