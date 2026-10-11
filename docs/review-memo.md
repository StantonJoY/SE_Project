# 评审备忘录（Review Memo）

> **D4 交付物** · 课程对应：note 行 5220–5231（DoD）、行 5241–5248（Sprint Review 六项检查）
> **要求**：每个 pull request 一份，覆盖**规格一致性 / 架构一致性 / 代码与测试质量 / 操作元数据**，
> 全程检查安全与效率，结尾给出 **APPROVE / CHANGES REQUIRED / REJECT** 之一。
> **状态**：V1 首份 · 日期：2026-10-06 · 评审对象：V1 架构工件 + D1 需求注册表（尚未提交）

---

## 1. 评审对象与范围

| 项 | 内容 |
|---|---|
| **变更范围** | D1 机器可读需求注册表、A1/A2/A5 架构分析、5 份 CORE 架构工件、ADR-001/002、D3/D4 治理文件、Tier 1 fitness function、测试改造 |
| **新增文件** | 15 个（见 §5 清单） |
| **修改文件** | `README.md`、`docs/HANDOVER.md`、`pyproject.toml`、`test/offline/{test_ads,test_scene,test_compliance,test_requirements_registry}.py`、`src/{ads,scene,compliance}/models.py`、`scripts/validate_requirements.py`、`docs/req/{requirements.yaml,req-schema.json}` |
| **PR 规模检查**（课程 DoD 第 2 条：≤ 5 文件 / 200 行） | ❌ **严重超标**——本次为架构奠基批次，含 15 新增 + 12 修改文件。**须拆分为多个 PR 后重新评审**（见 §6 结论） |
| **作者 / 人类所有者**（课程 DoD 第 1 条） | ⚠️ agent 撰写，**尚未指定具名人类所有者** |

---

## 2. 规格一致性（Spec Alignment）

**检查**：每条需求是否有 ID、类型、陈述、可机器检查的 fit criterion、MoSCoW 优先级、来源追溯。

| 检查项 | 结果 | 证据 |
|---|---|---|
| 全部需求有唯一语义化 ID | ✅ | `requirements.yaml`：22 基线 + 19 候选 |
| ID 类别前缀与 type 相容 | ✅ | `validate_requirements.py` 强制，含负向测试 |
| 非功能需求表达为 metric + threshold + verification | ✅ | 7 条非功能需求均带 `metric` 块 |
| 不变式有可操作 fallback 且优先级为 must | ✅ | schema 条件强制；负向测试覆盖 |
| 每条需求追溯来源 | ✅ | `source_refs` + 6 个来源；死来源检测已强制 |
| 旧编号可追溯 | ✅ | 39 条 `legacy_id` + `legacy_id_map`，双向一致性已强制 |
| **需求基线是否冻结** | ❌ **未冻结** | 10 个 `OQ` 待决；ADR 状态为 `Proposed` |

**结论：规格质量达标，但基线未冻结，不能进入 7 步探索循环的 Step 1。**

---

## 3. 架构一致性（Architecture Alignment）

| 检查项 | 结果 | 证据 |
|---|---|---|
| 每个决策可追溯到 ADR → REQ → Code → Tests → Monitoring | ⚠️ **部分** | `trace-matrix.md` §4 有 3 条完整链，覆盖 15/22 条需求；余 7 条未单列（`TD-005`） |
| 不变量登记册六字段齐全 | ✅ | 16 条，每条含 ID/Statement/Source/Enforcing/Verification/Fallback |
| 至少 1 条流程不变量 | ✅ | 3 条：`INV-ADS-009`/`010`/`011` |
| 每条不变量有可操作 fail-closed fallback | ✅ | 全部为 `no_ad` / 阻断加载 / 阻断合并 / 降级解释；`retry` 措辞已被校验器拦截并要求论证 |
| ADR 含 ≥3 评价准则 + 被否候选 + 度量式重开触发器 | ✅ | ADR-001：C1/C2/C3 三维 W/M/S + 2 个被否候选 + 7 个触发器；ADR-002：4 组备选 + 6 个触发器 |
| 四份工件命名零漂移 | ✅ | `compliance.pipeline.run_compliance` 等构件名在 requirements / asr-register / invariants / trace-matrix / blueprint 中一致 |
| Trace Matrix 五列填满且 monitor 具体可度量 | ✅ | 22 行全部为 `<指标> <比较符> <阈值>` 形式 |
| Memory Design 六字段齐全 | ✅ | `memory-design.md` §2–§3 |
| 蓝图 11 节齐全且位于根目录 | ✅ | `architecture-blueprint.md`，含 §5 权威分配、§6 四角色分离 |
| 运行时策略覆盖每条降级路径 | ✅ | 16 条策略（`RP-001`~`016`），含不变量层面兜底 |
| **架构债是否静默** | ✅ **不静默** | 12 条登记于 `debt-register.md`，均有来源与重开条件 |

**结论：架构工件体系完整且互相咬合（跨工件一致性由脚本强制），但追溯链有 7 条缺口。**

---

## 4. 代码与测试质量

| 检查项 | 结果 | 证据 |
|---|---|---|
| 结构约束 S1 一个元素一个模块 | ✅ | fitness function PASS |
| 结构约束 S3 ADR docstring 可追溯性 | ✅ | 11 个 `src/` 模块全部引用 ADR/REQ/INV ID |
| 验证约束 V1 fit criterion 覆盖 | ⚠️ **9/22** | 13 条已登记去向（`TD-009`）；P4~P6 未实现 |
| 验证约束 V2 不变量反例覆盖 | ⚠️ **5/16** | 11 条已登记去向；**三条流程不变量无反例测试**（最高优先） |
| 验证约束 V3 测试引用 REQ/INV | ⚠️ 模块级 ✅ / 函数级部分 | `TD-010` |
| 验证约束 V4 跨轮次无回归 | ✅ | 66 passed；既有测试模块未消失 |
| 三层验证 Tier 1 结构 | ✅ | `fitness_functions.py` |
| 三层验证 Tier 2 回归 | ✅ | pytest 全量通过 |
| 三层验证 Tier 3 行为 | ❌ **未建立** | 评估集待建（`TD-003`） |
| 测试是否伪造/迎合实现 | ✅ 无 | 覆盖表用 `test_backed: false` 诚实标注未覆盖项；**不伪造空测试** |
| 角色分离（Plan ≠ Build ≠ Verify） | ❌ **未满足** | 同一 AI 兼任（`TD-011`） |

**安全与效率专项**：

- **安全**：核心安全主张（零逃逸）有 12 项反例测试支撑；authority 边界 A1–A8 已文档化。但 `INV-ADS-009`/`010`（变更治理）**无任何强制机制**（`TD-002`）。
- **效率**：唯一运行时依赖 `jsonschema`；无数据库、无网络依赖（离线测试）。token 预算与延迟需求**已设计未实现**（`TD-004`）。

**代码质量缺陷**：`BUG-005`（测试硬编码素材条数 8）**已知未修**，理由与触发条件已记录。

---

## 5. 操作元数据（Operational Metadata）

| 项 | 内容 |
|---|---|
| **验证命令与结果** | `validate_requirements.py` → **PASS**（22 基线 / 19 候选）<br>`fitness_functions.py` → **PASS**（S1–S3、V1–V4、TRACE）<br>`pytest test/offline` → **66 passed, 0 error** |
| **新增文件清单** | `docs/req/requirements.yaml`、`docs/req/req-schema.json`、`docs/architecture/{asr-register,invariants,trace-matrix,memory-design,concern-clusters,runtime-policy-catalog,adr-001-guarded-hybrid,adr-002-fail-closed-and-governance}.md`、`architecture-blueprint.md`、`docs/code-governance/{structural-constraints,verification-constraints,acceptance-coverage-map.yaml}`、`docs/debt-register.md`、`docs/bug-diary.md`、`scripts/fitness_functions.py` |
| **依赖变更** | `pyproject.toml` dev 依赖新增 `PyYAML>=6.0` |
| **未提交残留** | ⚠️ `scripts/_renumber_v2_candidates.py`（一次性脚本，应删）、`.dsh_write_probe.tmp`（权限探查残留，应删）——见 `TD-012` |
| **AI 使用日志**（课程门禁第 6 条） | ❌ **未更新**——`docs/ai-use-log.yaml` 尚未创建。**按门禁规则，改动代码/工件而未更新 AI-use 日志应被阻塞** |
| **是否触及 safety-critical 路径** | ✅ 是：`docs/req/requirements.yaml`、`docs/architecture/invariants.md`、`data/*.json`（未改动）。按 ADR-002 D4 须**人工批准** |
| **回滚方式** | 全部为新增文件与文档修改，`git checkout` 即可回滚；无数据迁移、无 schema 变更（`data/*.json` 未动） |

---

## 6. 结论

### 判定：**CHANGES REQUIRED**

**理由（4 项阻塞）**：

| # | 阻塞项 | 依据 |
|---|---|---|
| 1 | **PR 规模严重超标**——15 新增 + 12 修改文件，远超 DoD 的 5 文件 / 200 行 | 课程行 5226；DoD 第 2 条 |
| 2 | **AI-use 日志未更新**——改动代码与工件却未同步日志 | 课程门禁第 6 条；`REQ-ADS-GOV-002` |
| 3 | **触及 safety-critical 路径但无人工批准**——`requirements.yaml` 与 `invariants.md` 属 ADR-002 D4 的受保护路径 | ADR-002 D4 |
| 4 | **未指定具名人类所有者** | 课程 DoD 第 1 条 |

**未阻塞但须跟进的 2 项**：

| # | 项 | 说明 |
|---|---|---|
| 5 | ADR-001/002 仍为 `Proposed` | 需人工批准后方可动 P4 代码（课程行 3830：计划获批前不得产出代码） |
| 6 | 测试与数据残留 `TD-012` 两个文件 | 提交前人工删除 |

### 建议的拆分方案（解决阻塞 1）

| 子 PR | 内容 | 规模 |
|---|---|---|
| **PR-A** | D1：`requirements.yaml` + `req-schema.json` + `validate_requirements.py` + `test_requirements_registry.py` | ~4 文件 |
| **PR-B** | A1/A2/A5：ASR 登记册 + 不变量登记册 + concern cluster | ~3 文件 |
| **PR-C** | 决策工件：ADR-001/002 + `architecture-blueprint.md` + `trace-matrix.md` + `memory-design.md` | ~5 文件 |
| **PR-D** | D3/D4：结构/验证约束 + 覆盖映射 + debt-register + bug-diary + fitness function | ~5 文件 |
| **PR-E** | 测试改造：`test_ads.py` 去 `tmp_path` + 三个测试模块补 docstring | ~4 文件 |

### Sprint Review 六项检查（课程行 5241–5248）

| 检查 | 结论 | 证据 |
|---|---|---|
| **Invariants** | ✅ 无违例（16 条均有 fallback；5 条已有反例测试） | `invariants.md`；负向测试 |
| **Trace Matrix** | ⚠️ 部分——22 条需求全部在矩阵中，但 7 条未单列决策链 | `TD-005` |
| **ADRs** | ✅ 与 blueprint 一致，无矛盾 | ADR-001 §8、ADR-002 §8 均双向引用 |
| **Architecture Diagram** | ⚠️ 无独立架构图——`blueprint.md` §3 仅含文本权威边界图 | 待补（见下） |
| **Architecture Debt** | ✅ 12 条全部记录，无静默 | `debt-register.md` |
| **Change Budget** | ❌ 本批次超标（见阻塞 1） | 本表 §1 |

### 补充发现（不在阻塞项内）

课程评分量规要求 **Diagram** 维度（note 行 5145）："AI 与确定性分离、超时与升级可见、自解释"。
本项目当前**没有独立架构图**，仅有 `architecture-blueprint.md` §3 的文本边界图。
**建议在 PR-C 中补一份架构图**（AI 建议域 / 确定性权威域分离，含超时与降级路径、失败归因回路）。

---

## 7. 评审人签署

| 角色 | 姓名 | 日期 | 判定 |
|---|---|---|---|
| 架构负责人（B） | ⏳ 待签 | | |
| 质量与治理负责人（D） | ⏳ 待签 | | |
| 人类所有者 | ⏳ **待指定** | | |

> 本备忘录由 AI 助手起草，**不构成自我批准**。课程行 5175：**No agent may self-approve.**
