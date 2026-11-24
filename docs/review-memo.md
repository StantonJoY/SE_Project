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
