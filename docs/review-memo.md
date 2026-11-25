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


## V2 AI proxy 复核记录（2026-10-31）

本轮技术审查由用户委托的监督代理完成，正式人工签署待确认。评审覆盖 19 条 V2 需求、确定性竞价、原子预算结算与审计、幂等，以及拒绝路径的零扣费。

独立测试暴露预算快照字段与整数评分接口的接线缺陷，监督代理要求 BUILD 按既有契约修复。随后复核发现 V1 评估漏判预期拒绝、仅改代码可绕过测试批准检查、Python 内嵌提示词变化未触发回放，分别补上阻断逻辑和反例。交互和技术决策摘要见 [AI 使用记录](ai-use-log.yaml)。

四条历史批准仍仅适用于其原范围。V2 的正式人工前置测试批准和最终验收待处理，远程 CI 和分支保护未核验。详见 [V2 审批状态](v2-approval-status.yaml)。


### V2 治理 BUILD 阶段记录（2026-10-31）

需求 schema（41 条）、fitness（21 测试模块，19 条 V2 实际符号与具体测试）、scripts/eval/新增治理测试 lint、依赖、实现一致性审计、安全 ADR 伴随检查、AI-use log 检查均通过。新增 test_v2_governance.py 为 20 passed（1.55s）。V1 replay 为 11/11 MUST_PASS、14/14 MUST_FAIL；V2 固定 replay 为 18 cases、0 violations，均通过。

该阶段 Gate 1 因缺少可信的 V2 人工前置测试批准而阻断。仓库完整性检查报告 17 个未跟踪交付物，三项 Git 跟踪回归失败。独立 TEST 随后迁移了三项假设只有 V1 版本或尚有 V2 候选的历史测试。

该阶段 bidding 语句覆盖率为 83.05%，低于 90% 门槛。随后由独立 TEST 补充结算边界反例。

### 本地技术复核记录（2026-10-31）

以下记录对应交付整理前的本地开发工作树。Git 跟踪失败来自当时尚未登记的新增文件。

| 检查 | 当次结果 |
|---|---|
| 全量离线测试 | 614 项通过，3 项 Git 跟踪检查失败 |
| `src/bidding` 语句覆盖 | 95.59%，门槛 90% |
| V1 / V2 固定回放 | V1 25 例（11 正向、14 预期拒绝）通过。V2 18 例（4 正向、14 预期拒绝）通过，违规数为 0 |
| 变异验证 | 25 项均检出。每项先验证无变异基线，凭调用阶段的行为失败确认检出 |
| 结构、静态和治理 | 需求 Schema、结构约束、Ruff、mypy、依赖、实现审计、ADR 伴随检查、语义回放触发和 AI 使用记录检查通过 |
| Gate 1 | 缺少 V2 人工前置测试批准，按原规则阻断 |
| 模型验证 | 本地 HTTP 边界及 SQLite 回归通过。CityU `/models` 返回 HTTP 200，V2 外部生成尚未运行 |

独立复核要求修正非法 Unicode 处理、HTTP 总时限及变异验证误判。修正后的变异工具排除导入、配置和签名错误。INV-ADS-015 改用真实的非法设备枚举反例验证素材 Schema。相关仓库证据见 [边界回归测试](../test/offline/test_v2_boundary_regressions.py)、[变异验证](../scripts/mutation_check.py)、[V2 评估器测试](../test/offline/test_v2_eval.py)。

仓库提供评审摘要、测试和可重跑的验证命令。原始会话、工具输出及干预注释在本地归档，由团队在课程要求时另行提交。部分协作正文在系统记录中仍为密文，无法导出为可读原文，D5 的完整可读会话要求仍有缺口。

### 上传前暂存预演（2026-11-05）

在隔离副本暂存本轮 26 个新增文件和 39 个已有文件的改动。Git 跟踪检查通过，候选提交不含原始会话、转写、原始运行日志或本机环境诊断。

| 检查 | 结果 |
|---|---|
| 完整性、Ruff、需求 Schema、架构约束、AI 使用日志 | 通过 |
| 全部离线测试 | 617 项通过 |
| 竞价模块语句覆盖率 | 95.59%，达到 90% 门槛 |
| V1 回放 | 11 条正向和 14 条预期拒绝均符合预期 |
| V2 回放 | 18 条符合预期，违规 0 项 |
| 实现前测试批准 | 仍阻断，涉及 14 个测试文件 |

本次结果来自本地暂存预演。正式前置批准状态见 [V2 审批状态](v2-approval-status.yaml)。

### CityU 真实调用与本地钩子复核（2026-11-05）

通过现有 V2 CLI 调用 `CS5351/DeepSeek-V4-Flash`。两个场景使用独立的本地 SQLite 账本，扣费是账本模拟值。

| 场景 | 实测结果 |
|---|---|
| 正常竞价 | 接受两个候选的合法评分。`ad_002` 通过合规检查后成交，扣 200 分，余额从 600 分变为 400 分，写入 1 条审计。CLI 端到端耗时 2.438 秒。 |
| 同 ID 重放 | 改用不可达的本地模型地址重放同一请求，程序返回原结果，审计仍为 1 条。 |
| 医疗品类拒绝 | 模型给 `ad_009` 打 85 分。合规层返回 `no_ad/compliance_rejected`，扣费 0，余额保持 200 分，写入 1 条审计。CLI 端到端耗时 2.454 秒。 |

这两次真实生成验证了接入和两条决策路径。质量评估、p95、真实费用和独立 live 测试套件仍待完成。

本机已安装现有 `pre-commit`，使用复用的 Python 3.12 环境。在隔离的暂存副本中，由 Git 执行钩子并通过了 ADR 伴随检查和 AI 使用日志检查。正式前置测试批准仍见 [V2 审批状态](v2-approval-status.yaml)。

同日通过 GitHub 公开接口核对 `main`，`protected` 为 `false`，适用规则列表为空。远端分支保护和评审者设置仍由管理员确认及配置。[分支保护说明](branch-protection.md)

---

## V3 复核记录（2026-11-22）

**复核对象**：`v3` 分支 → `main` 的合并（PR #3，merge commit `8b5a17a`，21 个提交）
**复核类型**：独立测试执行 + 本地门禁复跑。**不含具名人类的正式验收**——正式状态见
[`v3-approval-status.yaml`](v3-approval-status.yaml)。

| 维度 | 结论 | 证据 |
|---|---|---|
| 规格一致性 | 通过：61 条需求（V1 22 + V2 19 + V3 20）全部有 `enforcement` 与测试证据 | `req/requirements.yaml`、`acceptance-coverage-map.yaml` |
| 架构一致性 | 通过：9 个元素与 S1 一致；`bidding/`、`ads/`、`scene/` 在 V3 中零改动 | `git diff origin/main...v3`、`fitness_functions.py` |
| 代码与测试质量 | 通过：679 项离线测试、33/33 变异、三套 replay 违规 0 | `docs/testing/V3-Test-Report.md` |
| 操作元数据 | 通过：AI 使用日志已更新；ADR-006 已 `Accepted`；`CODEOWNERS` 已落地 | `ai-use-log.yaml`、`adr-006-*.md`、`.github/CODEOWNERS` |
| 真实模型 | PASS_WITH_LIMITATIONS：结构 30/30；标题诱导 5/5、名作对照 5/5 按标签选择 | `docs/testing/V3-Live-Prompt-Semantic-Report.md` |

**独立测试发现（8 项）**：F-001（manifest 哈希与文件不符，根因是生成器在 Windows 写出 CRLF）、
F-004（未跟踪文档阻断完整回归）、F-006（stdout 非 UTF-8）、F-007（13 项 lint）、F-008（门禁 1 映射缺口）
等；除 F-008 外均已关闭或修复，F-008 的处理见下。

**判定**：**ACCEPTED WITH DOCUMENTED GAP**

- 代码与测试证据充分，可合入；
- **门禁 1 对 V3 历史为红**：V3 测试实现于 2026-11-17，任何具名批准都无法早于它。
  处置：`TA-0005`（首条前置批准，2026-11-22T19:52，早于实现提交 19:53:34）+
  `TA-0006`（既有测试集的事后验收，明确不冒充前置批准）；缺口登记 `TD-018`；
- **不回填、不改校验器**是本次复核的明确约束。

**签署**：独立测试（测试成员）+ 本地复核（编码 agent）。**无具名人类签署**，
故本段不构成课程意义上的正式验收。

---

## PR 级评审缺口清单（2026-11-24）

> **性质声明**：本节是**缺口分析**，不是评审记录。它列出 `docs/review-memo.md` 距离
> 课程 D4「每个 pull request 一份评审」要求还差什么、差在哪、怎么补。
> **本清单不代替任何一次真实评审，不构成 APPROVE / CHANGES REQUIRED 判定，也不代签任何角色。**
> 新增实际评审时请另起一节，由具名人类签署。
>
> **2026-11-25 更新**：文末已回填 13 个已合入 PR 的逐条评审（见「PR 级评审记录（回填）」）。
> G1（PR 粒度）**部分消除**；G2（具名人类签署）**仍未消除**——回填评审不冒充人类评审。

### 0. 课程要求逐字口径

`docs/review-memo.md` 抬头已写明课程要求（note 行 5220–5231 DoD、行 5241–5248 Sprint Review）：

- 频率：**每个 pull request 一份**
- 四个维度：规格一致性 / 架构一致性 / 代码与测试质量 / 操作元数据
- 贯穿检查：安全与效率
- 收尾：给出 **APPROVE / CHANGES REQUIRED / REJECT** 之一

### 1. 现状（按 git 历史核对）

| 事实 | 值 | 来源 |
|---|---|---|
| `main` 上的提交数 | 约 40 个（V1 17 + V2 12 + V3 21，含合并提交） | `git log --oneline` |
| 实际走 PR 进 `main` 的次数 | **2 次已合入**（PR #1、PR #3）+ **若干仍 open**（PR #6 文档、PR #7 本仓库 README 纠错）。**注意：PR 编号以 GitHub 页面为准**，本节写作时（2026-11-24）观察到的 open PR 为 #1 / #6 / #7 | GitHub PR 列表 |
| `docs/review-memo.md` 里的评审段 | **4 段**：V1 首份（2026-10-06）、V2 AI proxy 复核（10-31）、V2 治理 BUILD + 本地技术复核（10-31）、V3 复核（11-22） | 本文件 §1–§7 与文末各节 |
| 其中对应"一个 PR"的 | **1 段**（V3 复核，明确对应 PR #3） | §「V3 复核记录」 |
| 具名人类签署数 | **0** | 各段签署栏 |

**结论**：不是"一份都没有"，而是**粒度不对 + 签署缺失**。

### 2. 缺口逐项

| # | 缺口 | 严重度 | 现状 | 为什么是缺口 |
|---|---|---|---|---|
| **G1** | **PR 粒度对不上** | 🔴 高 | 4 份评审覆盖的是"批次/阶段"，不是"每个 PR"；V1 那份评审的 27 个文件批次**从未真的拆成 5 个子 PR**就直推了 `main` | 课程 DoD 的意图是"每 PR 一小份"，评审一次控制在可读范围内。现在是一份评审覆盖整阶段，读起来像阶段总结而不是 PR 审查 |
| **G2** | **0 具名人类签署** | 🔴 高 | 三处签署栏全部"⏳ 待签"或"无具名人类签署" | 课程行 5175「No agent may self-approve」。无签署 = 没有发生过人类评审，无论 AI 复核多完整 |
| **G3** | **V1 首份判定 CHANGES REQUIRED 后无闭合记录** | 🟡 中 | 4 项阻塞（PR 规模、AI-use 日志、safety-critical 无批准、无具名所有者）当年均未按原样解除 | 一个 CHANGES REQUIRED 之后应当有"整改 + 复评"，否则读者无法判断这些阻塞后来怎么样了。实际是**绕过**（拆 PR 的建议没执行，直接推送了） |
| **G4** | **PR #1 / #6 无任何评审段** | 🟡 中 | PR #1（V2 竞价，draft）仍 open；PR #6（文档）刚开不久、尚未请求评审 | PR #1 是 draft 且已存在多日，可以写"暂缓合并"的明确判定；PR #6 刚开，**现在没有评审段是正常的**，不宜算缺口——应在其请求评审后补 |
| **G5** | **V2 那两段不是 PR 评审** | 🟡 中 | 参与者是 AI proxy / independent reviewer，标题已如实写明 | 不是造假，但**不能算作课程意义上的 PR 评审**——需要具名人类签署才能补足 |
| **G6** | **效率维度无任何记录** | 🟡 中 | 四维度里"安全"有覆盖（合规章节），"效率"完全没有 | 课程要求"全程检查安全与效率"。现有评审没有一处评估实现效率/性能代价 |
| **G7** | **缺 V1→V2→V3 之间的增量评审** | 🟢 低 | 12 个 V2 提交、21 个 V3 提交，除 V3 那次外没有逐段评审 | 这些提交都直推了 `main`。补写等于事后追认，风险高（见 §4「不建议做的事」） |

### 3. 缺口的主因

按时间顺序看，根因只有一条：**团队在 V1–V2 阶段没有走 PR 流程。**

- V1 的 17 个提交、V2 的 12 个提交，**全部直推 `main`**——2026-11-17 的会话记录里 agent 自己
  写道：「今天之前，一次 PR 都没有。所有提交直推 main，`review-memo` 是唯一一份评审记录，
  且判定是 CHANGES REQUIRED、签名栏全是待签。严格讲：没有一次代码评审实际发生过。」
- 分支保护与 CODEOWNERS 是 **V3 阶段（2026-11-22）** 才落地的。
- 所以"每 PR 一份"这条要求在 V1/V2 阶段**在物理上无法满足**——那时候根本没有 PR。

这不是可以事后补的：事后给直推的提交补写评审，等于伪造流程。

### 4. 不建议做的事（风险提示）

| 不要做 | 为什么 |
|---|---|
| **不要**给 V1/V2 的历史提交补写 PR 评审段 | 那些提交没有 PR 编号、没有 diff 边界、没有评审当时的上下文。补写出来的"评审"是虚构过程，一旦被追问提交顺序就站不住 |
| **不要**代签任何角色 | 课程行 5175。agent 起草的评审只能标注"AI 起草，待人类签署" |
| **不要**把 AI proxy 复核改称"人类评审" | 现有文本已如实区分，改称会破坏诚实性，且更容易被查 |
| **不要**回填签署日期 | 与 `docs/test-approvals.yaml` 里 TA-0006 的先例一致：事后确认必须显式承认"不满足时序"，不得回填 |

### 5. 可以做的补法（按风险从低到高）

#### 补法 A：从当前 PR 起，逐个补真人评审（推荐）

**做法**：从 PR #6 / 你正在开的 README PR 起，每一个 PR 在 `docs/review-memo.md` 新增一节，
节内四维度 + 效率 + 判定 + **具名人类签署**。

**代价**：每个 PR 约 30–40 分钟（读 diff + 写四维度）。
**收益**：从今往后"每 PR 一份"成立，且全部可核查。
**风险**：低——只新增，不改历史。

#### 补法 B：在 review-memo 顶部加一节「评审覆盖说明」，把缺口讲清楚

**做法**：说明"V1/V2 阶段为直推，无 PR 可评；从 V3 起走 PR 流程；PR #3 为首次完整 PR 评审"。
**代价**：15 分钟。
**收益**：读者不会误以为遗漏，评阅老师看到的是**自我披露**而不是**隐藏**。
**风险**：低。**建议与 A 一起做。**

#### 补法 C：把 V3 那次评审重构成"PR #3 模板"

**做法**：给 V3 复核节补上"PR 编号 / diff 范围 / 文件数 / 行数 / 评审人 / 判定"这几个 PR 元字段。
**代价**：20 分钟。
**收益**：让已有的一份看起来就是标准的"每 PR 一份"，后续照此复制。
**风险**：低——V3 确实是经过 PR 的，补元字段不是虚构。

#### 补法 D：给 PR #1 / #6 各写一段"暂缓 / 待评审"记录

**做法**：两个 PR 各写 5–10 行：范围、当前状态（未评审 / 卡在 Gate 5）、下一步。
**代价**：10 分钟。
**收益**：消灭 G4。
**风险**：低。

#### 不建议的补法 E：回填历史

见 §4。

### 6. 优先级建议

1. **先做 B**（15 分钟，消除最大误解风险）——这是本清单的核心建议；
2. **再做 C**（20 分钟，让已有证据标准化）；
3. **A 是持续动作**，从下一个 PR 开始执行；
4. **D 可选**，视老师是否追问 PR #1 而定。

**整体判断**：D4 的缺口是**流程缺口**（V1/V2 没有 PR），不是**文档缺口**（review-memo 里
其实有 4 段实质评审）。如实披露 + 从 PR 流程建立之日起严格执行，是唯一不引入伪造的补法。

### 7. 相关登记

- `docs/debt-register.md` 的 TD 列表里目前**没有**"每 PR 一份评审"这一条，建议新增
  `TD-029`（评审粒度与签署缺口），状态 `open`，处置指向本清单。
  > 注：`debt-register.md` 属 `scripts/check_safety_paths.py` 的 `[仅只读]` 路径，
  > 追加 `TD-029` 不需要 ADR，但需由人工确认后提交。
- `docs/plans/REMAINING-WORK.md` 的 RW-15 覆盖的是"PR 路径两条规则验证"，
  与本缺口相关但不同——RW-15 测的是**能不能合**，本清单问的是**合之前有没有评审**。

---

## PR 级评审记录（回填 · 2026-11-25）

> **性质声明（必读）**
>
> - 本节是**对已合入 PR 的事后评审**（retrospective），**不是**合并前的前置评审。
>   本仓库 2026-11-17 起才有 PR 流程，V1 的 17 个提交从未走 PR（见上文缺口清单 G1）。
> - 判定适用于**该 PR 合入的最终内容**，不代表当时的合并决策经过了本节流程。
> - **署名来源（重要）**：13 条评审的署名由项目所有者 Shen Jiyun 于 2026-11-25 **授权补录**，
>   按「谁负责该区域」分配，依据是各 PR 的提交作者（`git log` 可核）。
>   署名表示**项目层面的评审责任归属**，不等同于每位成员逐字读过该 PR；
>   如需逐人确认，请各自确认后在本节留痕。记录方式逐条标注为「PM 代录」。
> - **无独立第三方签署**：四条记录均由团队内部产生，课程要求的「具名人类」在此指团队成员，
>   不是校外评审者。
> - 四维按课程 DoD：规格一致性 / 架构一致性 / 代码与测试质量 / 操作元数据；另附安全与效率。

### 1. 已合入 PR 总览

| PR | 日期 | 分支 | merge | 规模 | 范围 | 判定 |
|---|---|---|---|---|---|---|
| #2 | 2026-11-17 | `main-v2` | `143cba6` | 5 提交 / 211 文件 | V2 竞价 + 原子账本 + CI 修复 | **APPROVE（附条件）** |
| #3 | 2026-11-22 | `v3` | `8b5a17a` | 21 提交 / 217 文件 | V3 语料 / 内容分级 / 定价 / 提示词 | **APPROVE（附条件）** |
| #4 | 2026-11-22 | `docs/v3-final-demo-video` | `6578062` | 1 / 4 | 演示视频 | APPROVE |
| #5 | 2026-11-22 | `docs/v2-self-evaluation` | `7c459c9` | 1 / 1 | V2 自评 | APPROVE |
| #7 | 2026-11-25 | `readme-fact-correction-1` | `0dfc66e` | 2 / 1 | README 事实纠错 | APPROVE |
| #9 | 2026-11-25 | `docs/report-member-d` | `c69cf04` | 1 / 1 | 报告 D 自评 | APPROVE |
| #10 | 2026-11-25 | `fix-pyproject-scripts-import-1` | `d67ed09` | 1 / 1 | 修 editable 安装让 scripts 可导入 | APPROVE |
| #12 | 2026-11-25 | `docs-td-status-field` | `f05dfe2` | 2 / 1 | 28 条 TD 加状态字段 | APPROVE |
| #13 | 2026-11-25 | `main` | `ac2fa77` | 2 / 1 | 分支同步 | APPROVE |
| #14 | 2026-11-25 | `docs-branch-protection-status` | `504151a` | 1 / 1 | 分支保护状态更新 | APPROVE |
| #15 | 2026-11-25 | `docs-transcripts-annotations` | `8a0df74` | 4 / 4 | 会话记录加干预索引 | APPROVE |
| #16 | 2026-11-25 | `Frankgyb-patch-1` | `a36f4d0` | 1 / 1 | 评审缺口清单 | APPROVE |
| #17 | 2026-11-25 | `docs-architecture-artifacts` | `25865f0` | 4 / 4 | 四份架构工件 | APPROVE |
| #18 | 2026-11-25 | `report-member-b-self-eval` | `d8d4bc2` | 1 / 1 | 报告 B 自评 | APPROVE |

### 2. 实质 PR 的逐条评审

#### PR #2 · V2 竞价与原子账本

**范围**：`src/bidding/`（模型 + 引擎 + 账本）、`src/app/pipeline_v2.py`、`src/app/cli_v2.py`、
`eval/v2_*`、`docs/architecture/adr-005-*`；同时修复 CI（workflow 级 `${{ runner.temp }}` 非法引用）。

- **规格一致性**：19 条 V2 需求逐条有 `enforcement` 与测试（`test_bidding_v2` / `test_pipeline_v2`）；PASS。
- **架构一致性**：竞价插在"模型建议"与"合规否决"之间，合规章受否决权未被削弱（`INV-V2-003` 有反例）；
  `bidding/` 未导入 `compliance/`，权威边界未倒置。PASS。
- **代码与测试质量**：金额统一整数分；`Ledger.finalize` 在单事务内写预算/结果/审计，注入故障可回滚
  （`INV-V2-004`）；12 条变异全部被检出。PASS。
- **操作元数据**：审计含 `model_version` / `policy_version` / 配置来源；AI-use 日志有记录。PASS。
- **安全与效率**：`V2_LLM_API_KEY` 只作环境变量名，值不入库、不打印、不进审计；无新增依赖。PASS。
- **判定**：**APPROVE（附条件）**
- **条件**：① 门禁 1 对 V2 测试为红（测试与实现同批产出，无法追溯前置批准）→ 已登记 `TD-018`，
  `TA-0006` 作事后验收；② PR 规模 211 文件，远超可审范围（`review-memo` 的缺口 G1 即指此）。
- **评审人**：Gong Yuebin (60652349) · **签署时间**：2026-11-25T20:05+08:00 · **记录方式**：PM 代录（三位作者 StantonJoY / Zhang Qiyan / Gao Zhechun 均不参与自评）

#### PR #3 · V3 语料接入 / 内容分级 / 定价接入

**范围**：`src/corpus/`（新元素）、`src/compliance/content_rules.py`、`src/app` 接线、
`data/corpus/`（5,000 行）、`data/bids-corpus.json`、`eval/v3_*`、`docs/testing/` 证据包、`ADR-006`（D1–D9）。

- **规格一致性**：20 条 V3 需求全部有 `enforcement` 与测试；`REQ-ADS-FR-012`（5% 定价）有数值断言与
  sidecar 复算测试。PASS。
- **架构一致性**：投影旁路使 `AD_SCHEMA` 未变（`INV-V3-001` 有加载路径反例）；内容分级在既有 `scene`
  步骤内实现，五步顺序未变（`INV-V3-005` 有变异）；`policy=None` 与 V1 逐位一致（有等价性测试）。PASS。
- **代码与测试质量**：679 测试；变异 33/33；三套 replay 违规 0；V3 新模块覆盖率 86%。PASS。
- **操作元数据**：`provenance.prompt_version` 升到 `ctx-v1.1`；AI-use 日志 `AIU-0028`；证据包完整。PASS。
- **安全与效率**：内容分级为"并集判据 + 年龄兜底"（覆盖 8,877 条只有 warnings 的记录）；
  V1 语料请求 0.74 s、V2 1.4 s，均在预算内。PASS。
- **判定**：**APPROVE（附条件）**
- **条件**：门禁 1 对 V3 历史为红（`TD-018`）；`ADR-006` 在合并时为 `Proposed`，后于 2026-11-22 补为 `Accepted`。
- **评审人**：Gong Yuebin (60652349)、Zhang Qiyan (60805659) · **签署时间**：2026-11-25T20:05+08:00 · **记录方式**：PM 代录（作者 StantonJoY / Gao Zhechun 不参与自评）

#### PR #10 · 修复 editable 安装，让 scripts 可导入

**范围**：`pyproject.toml`（1 文件）。

- **规格一致性**：对应 `REQ-ADS-NFR-QA-002`（门禁必须可运行）；此前 `scripts/` 无法作为包导入，
  导致多道门禁在 CI 中失败。PASS。
- **架构一致性**：不改变模块边界，仅补 packaging 声明。PASS。
- **代码与测试质量**：修复后 6 道门禁恢复可运行；此前 CI 红与代码质量无关（工具链问题）。PASS。
- **操作元数据**：commit 说明写明"unblock all CI gates"。PASS。
- **安全与效率**：无依赖新增，无安全面变化。PASS。
- **判定**：**APPROVE**
- **评审人**：Shen Jiyun (60989886) · **签署时间**：2026-11-25T20:05+08:00 · **记录方式**：PM 签署（作者 Gong Yuebin 不参与自评）

#### PR #17 · 四份架构工件

**范围**：`permission-model.md`（D2#6）、`risk-list.md`（D2#10）、`option-ledger.md`（D2#11）、
`evaluation-logbook.md`（D2#9）。

- **规格一致性**：补齐课程 D2 点名的 permission model（文件级读写权限、默认无权限、逐路径白名单），
  以及三份可选工件。PASS。
- **架构一致性**：permission model 与 `AGENTS.md` 的角色表一致；风险清单逐条给"假设 → 触发 → 复查"。
  PASS。
- **代码与测试质量**：纯文档，无代码路径影响；`check_repo_completeness` 通过（已跟踪）。PASS。
- **操作元数据**：提交说明逐份对应 D2 编号，可追溯。PASS。
- **安全与效率**：权限模型把"默认拒绝"写成显式规则，属安全增强。PASS。
- **判定**：**APPROVE**
- **评审人**：Shen Jiyun (60989886) · **签署时间**：2026-11-25T20:05+08:00 · **记录方式**：PM 签署（作者 Gong Yuebin 不参与自评）

#### PR #12 / #13 · 分支同步

**范围**：合并提交与 `debt-register.md` 的状态字段（1 文件）。

- **判定**：**APPROVE**——#13 为 `main` 同步（无独立内容），#12 为 28 条 TD 补 `status` 字段，
  与 `REMAINING-WORK.md` 的 `RW-18` 一致。
- **评审人**：Shen Jiyun (60989886) · **签署时间**：2026-11-25T20:05+08:00 · **记录方式**：PM 签署（作者 Gong Yuebin 不参与自评）

### 3. 文档类 PR 批量评审

| PR | 内容 | 规格 | 架构 | 质量 | 元数据 | 安全/效率 | 判定 |
|---|---|---|---|---|---|---|---|
| #4 | 演示视频（4 文件） | n/a | n/a | 证据可复现（脚本+截图） | 文件名含日期 | 无影响 | APPROVE |
| #5 | V2 自评 | 对应 D6 | n/a | 300–500 词区间内 | 提交署名 | 无影响 | APPROVE |
| #7 | README 事实纠错 | 与仓库现状一致 | n/a | 单文件纠错 | 说明写明"fact correction" | 无影响 | APPROVE |
| #9 | 报告 D 自评 | 对应 D6 | n/a | 字数达标 | 提交署名 | 无影响 | APPROVE |
| #14 | 分支保护状态 | 与实测一致（§9 三段对照） | n/a | 含失败/成功证据 | 有日期 | 无影响 | APPROVE |
| #15 | 会话记录干预索引 | 对应 D5 | n/a | 每份含干预点与理由 | 4 份同步 | 无影响 | APPROVE |
| #16 | 评审缺口清单 | 对应 D4 | n/a | 自陈不足，未冒充评审 | 注明日期 | 无影响 | APPROVE |
| #18 | 报告 B 自评 | 对应 D6 | n/a | 字数达标 | 提交署名 | 无影响 | APPROVE |

### 3.1 文档类 PR 的署名清单

| PR | 责任评审人 | 签署时间 | 记录方式 |
|---|---|---|---|
| #4 演示视频 | Shen Jiyun (60989886) | 2026-11-25T20:05+08:00 | PM 签署（作者 Gao Zhechun 不参与自评） |
| #5 V2 自评 | Gong Yuebin (60652349) | 2026-11-25T20:05+08:00 | PM 代录 |
| #7 README 纠错 | Shen Jiyun (60989886) | 2026-11-25T20:05+08:00 | PM 签署（作者 Gong Yuebin 不参与自评） |
| #9 D 自评 | Shen Jiyun (60989886) | 2026-11-25T20:05+08:00 | PM 代录 |
| #14 分支保护状态 | Shen Jiyun (60989886) | 2026-11-25T20:05+08:00 | PM 签署 |
| #15 会话记录注释 | Shen Jiyun (60989886) | 2026-11-25T20:05+08:00 | PM 签署 |
| #16 评审缺口清单 | Shen Jiyun (60989886) | 2026-11-25T20:05+08:00 | PM 签署 |
| #18 B 自评 | Shen Jiyun (60989886) | 2026-11-25T20:05+08:00 | PM 签署 |

> **两份自评（#5/#18/#9）的额外要求**：课程规定自评**由本人撰写**。本节只能确认"字数与格式达标"，
> **不能确认作者身份**——需三位成员各自确认。

### 4. 未评审 / 未合并

| PR | 状态 | 说明 |
|---|---|---|
| #1 | **open（draft）** | V2 竞价的首版草案，已被 PR #2 取代；建议关闭，关闭理由写明"内容已并入 #2" |
| #6 | open | 文档类，创建后未请求评审；合并前需补本节格式的评审 |

### 5. 本节之后的前向规则

1. 每个新 PR 在合并前必须补一节，模板：

   ```markdown
   #### PR #<编号> · <标题>
   **范围**：<改了哪些目录/文件，规模>
   - 规格一致性：<对应哪些 REQ/INV，证据文件>
   - 架构一致性：<是否触及权威边界/受保护路径，是否伴随 ADR>
   - 代码与测试质量：<测试数/变异/replay，若有>
   - 操作元数据：<版本号/AI-use/审计字段>
   - 安全与效率：<注入面/依赖/性能>
   - 判定：APPROVE / CHANGES REQUIRED / REJECT
   - 评审人：<具名人类> · 签署时间：<ISO 8601>
   ```

2. **评审 ≠ 测试批准**：`TA-*`（门禁 1）是独立门禁，评审通过不替代前置测试批准。
3. **无具名签署的评审不计入 D4 合规**——本节的 13 条全部缺签署（G2），这一条只能由人来补。
