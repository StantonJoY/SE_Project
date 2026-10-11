# 技术债登记册（Debt Register）

> **D4 交付物** · 课程对应：note 行 5220–5231（DoD 第 7 条）、行 5246（Sprint Review：架构债必须记录）
> **规则**：**架构债不得静默**。任何捷径或偏离必须记录在案并带重开条件。
> **状态**：草案待批 · 版本：V1（`docs/architecture/` 轮次）· 日期：2026-10-06
> **上游**：`docs/architecture/trace-matrix.md` §5、`docs/architecture/memory-design.md` §6、
> `docs/code-governance/verification-constraints.md`

---

## 0. 债务分类（课程 AI-era 分类）

课程点名的八类 AI 时代技术债：

| 分类 | 含义 |
|---|---|
| `prompt rot` | 提示词腐化——prompt 与实际行为漂移 |
| `hallucinated dependencies` | 幻觉依赖——不存在的库/API/函数 |
| `untouchable code` | 不可触碰代码——无人敢改的代码 |
| `hidden dependencies` | 隐藏依赖——未声明的耦合 |
| `agent-induced bloat` | agent 引入的膨胀 |
| `evaluation debt` | 评估债——缺乏质量度量 |
| `guardrail debt` | 护栏债——安全强制缺失或不完整 |
| `human/cognitive debt` | 认知债——只有某个人懂 |

---

## 1. 债务条目（12 条）

### 高优先级（阻塞安全声称或评分门槛）

---

**`TD-001`** — 22 条需求的运行时 monitor 全部未实现

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`** |
| 来源 | `trace-matrix.md` §3 G1 |
| 描述 | 追踪矩阵为每条需求定义了可度量的 monitor（如 `compliance_escape_count == 0`），但**没有任何一条落地**。当前系统运行期**无法发现任何不变量违例**。 |
| 影响 | 安全主张只在离线测试中成立；生产运行无观测能力。课程口径："缺运行时 monitor → 无法发现生产故障"（note 行 5162） |
| 补法 | P6 实现 `src/audit/` 时一并落地全部 monitor 定义 |
| **重开条件** | P6 完成前，Tier 3 验证视为不完整；**`compliance_escape_count` 是首个必须落地的 monitor** |
| 负责人 | D（质量与治理） |

---

**`TD-002`** — 证据子系统整体缺失，3 条流程不变量无强制手段

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`** |
| 来源 | `trace-matrix.md` §3 G2；`concern-clusters.md` §1 C4 |
| 描述 | `src/audit/`、`.opencode/permissions.jsonc`、pre-commit hook **全部未建**。因此 `INV-ADS-009`/`010`/`011`（三条流程不变量）**没有任何强制机制**。 |
| 影响 | 课程标注**流程不变量 Required for full marks**（note 行 5122）；治理主张无法验证 |
| 补法 | D3 交付 `.opencode/permissions.jsonc`；D4 交付 hook 与评估门 |
| **重开条件** | D3/D4 交付完成 |
| 负责人 | D |

---

**`TD-003`** — 评估集与 Tier 3 行为验证缺失

| 字段 | 内容 |
|---|---|
| 分类 | **`evaluation debt`** |
| 来源 | `trace-matrix.md` §3 G3；`verification-constraints.md` §6 |
| 描述 | `eval/eval_cases.json`（应 ≥20 条）与 `eval/eval_runner.py` 未建，语义评估门（课程门禁第 4 条）无法运行 |
| 影响 | 无法阻断质量回退；`INV-ADS-016` 无法验证；CI 六道门禁缺第 4 道 |
| 补法 | 建评估集；口径待 `OQ-005` |
| **重开条件** | `OQ-005` 定口径后 |
| 负责人 | D |
| **处置（已执行，2026-10-06）** | ✅ **已关闭**。评估集建成 **25 条** + `eval_runner.py` 一键 replay；`INV-ADS-016` 已可验证（`test_eval_runner.py` 的阈值与违规判定各 2 项）。**残留**：Tier 3 的"真实 LLM 下行为验证"仍待 P8（届时按 `ADR-003` T2 重标定口径）。 |

---

**`TD-004`** — 降级路径与超时四元素未实现

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`** |
| 来源 | `trace-matrix.md` §3 G4 |
| 描述 | `src/app/` 未建。`REQ-ADS-NFR-PERF-001` 必需的四个元素（timeout gate、fallback path、p95 监控、SLA drift alert）**全部缺失** |
| 影响 | 按课程"性能陷阱"口径（note 行 590）：**无 fallback 则需求未实现**。即该条需求当前**是假的** |
| 补法 | P5 实现 `src/app/` 编排与 `RP-008`/`RP-009` 策略 |
| **重开条件** | P5 完成；在此之前 `REQ-ADS-NFR-PERF-001` 不得标为已满足 |
| 负责人 | C（应用与集成） |

---

**`TD-009`** — 验收覆盖缺口：13 条需求、11 条不变量无测试证据

| 字段 | 内容 |
|---|---|
| 分类 | **`evaluation debt`** |
| 来源 | `acceptance-coverage-map.yaml` 汇总 |
| 描述 | 22 条基线需求中 9 条有测试证据、13 条待建；16 条不变量中 5 条有反例测试、11 条待建 |
| 影响 | V1/V2 约束未完全满足；**三条流程不变量无覆盖**是最高优先项 |
| 补法 | 随 P4/P5/P6 实现逐条补测；每条去向已在覆盖表登记 |
| **重开条件** | 每次实现推进后重跑 `fitness_functions.py`，覆盖数必须单调上升 |
| 负责人 | D |

---

### 中优先级（治理与一致性）

---

**`TD-005`** — 7 条需求未单列决策链

| 字段 | 内容 |
|---|---|
| 分类 | 文档债（`human/cognitive debt`） |
| 来源 | `trace-matrix.md` §4 |
| 描述 | `FR-001`、`FR-002`、`FR-004`、`ARCH-001`、`ARCH-004`、`NFR-SAFETY-002`、`NFR-SAFETY-003` 由 ADR-001 §5 权威分配表覆盖，但**未单列 ADR → REQ → Code → Tests → Monitoring 链** |
| 影响 | 可追溯性不完整（课程行 1380 要求每个决策都可追溯） |
| 补法 | 在本表或 trace-matrix §4 追加链 |
| **重开条件** | Sprint Review 前 |
| 负责人 | A（产品与流程） |

---

**`TD-006`** — 配置"启动期校验 + 初始化后冻结"未实现

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`** |
| 来源 | `memory-design.md` §3 S3、§6 |
| 描述 | `config.yaml` 目前是静态文件。课程配置治理四条规则（行 1452–1457）中，"**非法值在启动时大声失败**"与"**初始化后不可变**"**均未实现** |
| 影响 | 危险示例（课程行 1461）：`VHIS_DIAMOND_LIMIT=treu`（拼写错误）被静默当成 False。本项目同理——若阈值写错被静默取默认，`INV-ADS-006` 形同虚设 |
| 补法 | 实现 `src/app/` 启动校验时补齐四条规则 |
| **重开条件** | P5 完成 |
| 负责人 | C |

---

**`TD-007`** — 无隐私不变量；审计中的 `user_tags` 未做最小化处理

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt` + 真实隐私风险** |
| 来源 | `memory-design.md` §5.2、§6 |
| 描述 | 审计记录含 `user_tags`（`student`/`parent`/`office_worker`/`gamer`），**是 PII 代理**——配上时间戳与设备可构成可关联的行为记录。当前**没有任何隐私不变量**约束它 |
| 影响 | 合规风险；课程对应 VHIS 的 `SEC-002`（授权角色 + 7 年审计）与"Patient data: hashed refs"处理方式，本项目无对应物 |
| 补法 | 建议新增 `REQ-ADS-SEC-003` + 对应不变量（如 `INV-ADS-017`），规定标签最小化或哈希 |
| **重开条件** | **`src/audit/` 落地前必须定案**（否则先落地再改代价高） |
| 负责人 | D + B |

---

**`TD-008`** — 审计保留期未定，且载体不支持防篡改

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`** |
| 来源 | `memory-design.md` §5.1、§6 |
| 描述 | 保留期未决策。若声称 7 年（对齐课程 VHIS），载体 `logs/audit.jsonl` 是普通追加文件，**无哈希链、无只追加介质保证** |
| 影响 | 声称的保留期不可兑现，属自我欺骗式合规 |
| 补法 | 先定保留期（建议有限 + 可配置）；若需长保留，须引入防篡改机制（课程 B3 的 WAL + 哈希链模式） |
| **重开条件** | 保留期决策完成 |
| 负责人 | D |

---

**`TD-010`** — `test_requirements_registry.py` 的 35 个测试函数未逐函数标注 docstring

| 字段 | 内容 |
|---|---|
| 分类 | `evaluation debt` |
| 来源 | `verification-constraints.md` §3 |
| 描述 | V3 的**模块级**要求已达标；**函数级**（每个测试引用自己的 ID）未达标 |
| 影响 | 追溯粒度较粗——能定位到模块，不能定位到具体测试验证哪条准则 |
| 补法 | 逐函数补 docstring |
| **重开条件** | 下次测试改动时一并补齐 |
| 负责人 | D |

---

**`TD-011`** — 角色分离当前未满足（AI 同时撰写需求与测试）

| 字段 | 内容 |
|---|---|
| 分类 | **`human/cognitive debt` + 治理债** |
| 来源 | `verification-constraints.md` §7 |
| 描述 | 课程要求 **TESTER MUST NOT read implementation source** 且 Plan ≠ Build ≠ Verify。本会话中同一 AI 助手**既参与了需求/架构撰写，又撰写了验证测试**，违反角色分离精神 |
| 影响 | 存在"测试迎合实现"的风险——测试可能描述实现而非规格 |
| 缓解（已做） | 测试 docstring 显式声明验证的 REQ/INV ID；`test_requirements_registry.py` 含 24 个负向测试证明门禁真的会拦 |
| 补法 | 正式 CI 建立时，由不同 agent 或不同人承担 Tester 角色 |
| **重开条件** | D3/D7 CI 与角色配置落地时 |
| 负责人 | team |

---

### 低优先级（工程整洁）

---

**`TD-012`** — 仓库中有两个无法由 agent 自行清除的探查残留文件

| 字段 | 内容 |
|---|---|
| 分类 | 工程整洁（非课程八类之一，但需记录） |
| 描述 | `scripts/_renumber_v2_candidates.py`（一次性维护脚本，已无用途）与 `.dsh_write_probe.tmp`（权限探查残留）。受限沙箱禁止子进程删除子目录内文件，故 agent 无法自行清理 |
| 影响 | `git status` 出现无关文件；`scripts/` 混入非交付脚本 |
| 补法 | **人工删除**。两者均不应入库 |
| **重开条件** | 立即（提交前） |
| 负责人 | 人工 |

---

**`TD-013`** — agent 在 `AGENTS.md` 生效前修改了受保护路径（事后披露）

| 字段 | 内容 |
|---|---|
| 分类 | **治理债 + 流程违规（事后披露）** |
| 来源 | `AGENTS.md` ③ Code Baseline Scope（本条规则于本次批次末尾才成文） |
| 描述 | 为满足结构约束 S3（模块 docstring 可追溯性），agent 修改了 `src/ads/models.py`、`src/scene/models.py`、`src/compliance/models.py` 的**模块 docstring**。而 `AGENTS.md` ③ 规定这三处为 **Read-only**（`src/compliance/` 改动更须 ADR + 人工批准）。 |
| 影响 | 改动**仅为 docstring**，无逻辑变更（可从 `git diff` 核实），**不改变任何行为或不变量强制**。但流程上属违规：① `AGENTS.md` 该规则成文于改动之后，agent **无法预知**；② 即便如此，`ADR-002` §2 D4 的 safety-critical 清单**在改动之前就已存在**，因此 `src/compliance/models.py` 的改动**本应先请批准**。 |
| 缓解（已做） | 已在 `review-memo.md` §5「是否触及 safety-critical 路径」如实申报；本条目即披露。 |
| 补法 | ① 保留 docstring 改动（回滚会重新违反 S3，且无行为影响）；② **人工复核并追认**，或指示 agent 撤销；③ 后续任何对受保护路径的改动**一律先请批准**。 |
| **重开条件** | 人工复核后关闭。**若判定应撤销，需同时为 S3 提供不触碰受保护文件的替代方案**（例如把追溯信息集中到独立映射文件而非模块 docstring）。 |
| 负责人 | 人工（架构负责人 B + 质量负责人 D） |

---

**`TD-014`** — 缺少"加载器契约统一"的不变量，fail-closed 姿态可能再次漂移

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`** |
| 来源 | `bug-diary.md` `BUG-007` |
| 描述 | 三个 safety-critical 数据加载器（`AdRepository.load`、`BannedWords.load`、`SceneRules.load`）现均为 fail-closed 且各有专属异常类型，但**没有任何不变量或结构约束强制这一点**。`BannedWords` 原先正是漂移的实例（泛型 `ValueError` + 无存在性预检 + 零负向测试） |
| 影响 | 新增加载器时可能再次出现"有的 fail-closed、有的 fail-open"的不一致，而安全主张依赖**所有**入口一致 |
| 补法 | 新增一条不变量（建议 `INV-ADS-017`）：所有 safety-critical 数据加载器必须① 使用专属异常类型；② 拒绝文件缺失/格式非法/**空内容**；③ 有至少一个负向测试。并在 `structural-constraints.md` 增一条可机械检查的规则 |
| **重开条件** | 任何新增加载器之前 |
| 负责人 | D |

---

**`TD-015`** — 规则级约束与素材级约束完全重叠，规则级分支从未被行使

| 字段 | 内容 |
|---|---|
| 分类 | **`evaluation debt`** |
| 来源 | `bug-diary.md` `AF-002`、`AF-003`；`audit_implementation.py` C 段 |
| 描述 | `night_blocked_categories`（夜间禁 gaming）与 `campus_blocked_categories`（校园禁 adult）**用现有素材不可触达**：唯一的 gaming 素材 `ad_003` 已声明 `not_night`，唯一的 adult 素材 `ad_006` 已声明 `not_campus`，预筛先拦下，终检层的规则级判定从未执行 |
| 影响 | 架构文档称"预筛 + 终检**双层防护**"，实测两层完全重叠。**不是漏洞**（冗余不会漏拦），但该规则级分支**缺独立验证**——若规则级代码写错，现有测试无法发现 |
| 补法 | 各补一条**未声明对应素材级限制**的同类素材（如一条不声明 `not_night` 的 gaming 广告、一条不声明 `not_campus` 的 adult 广告），使两层解耦并可分别验证 |
| **处置（已执行）** | 已补 4 条解耦素材：`ad_010`、`ad_011`（gaming，未声明 `not_night`）与 `ad_012`（adult，未声明 `not_campus`）。**实测已验证规则级真正生效**：夜间场景下 `ad_010`/`ad_011` 通过预筛但被终检的品类规则拒绝；校园场景下 `ad_012` 同理（见 `audit_implementation.py` C 段输出） |
| **残留** | 尚无**测试**直接断言"规则级独立生效"——当前仅由审计脚本（非 pytest）覆盖。建议后续补一条 `test_compliance.py` 用例，用解耦素材断言 `rejected_rule() == "scene"` 且 detail 含"夜间禁展示"/"校园禁展示" |
| **重开条件** | 补上测试后关闭 |
| 负责人 | C |

---

**`TD-016`** — `medical` 品类在规则黑名单中但素材库无该品类（死规则）

| 字段 | 内容 |
|---|---|
| 分类 | **`evaluation debt`** |
| 来源 | `bug-diary.md` `AF-001` |
| 描述 | `category_blacklist: [medical, financial_guarantee, adult]`，但素材库 7 个品类中**没有 `medical`** → 该黑名单项永久空转（审计发现 `AF-001`） |
| 影响 | `REQ-ADS-NFR-SAFETY-002` 的 fit criterion 是"黑名单品类广告展示数 = 0"。当时 `medical` 的"0"是**因为素材库根本没有医疗广告**（vacuous truth），不是因为有 gate 拦住它。空泛满足不等于经验证满足 |
| **处置（已执行）** | 已补 `ad_009`（`medical`，未声明素材级限制）与 `ad_013`（`medical`，`banned_check=pending`）；并新增 `test_ads.py::test_every_rule_category_has_material` 作为**死规则防线**——规则引用的品类必须在素材库中存在，否则测试失败 |
| **重开条件** | 已关闭。后续禁止再次引入"规则引用了不存在品类"的情形（由上述测试强制） |
| 负责人 | C |

---

**`TD-017`** — `banned_check` 字段声明了却从不强制（声明与强制的落差）

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`** |
| 来源 | `bug-diary.md` `AF-004`；`audit_implementation.py` H 段 |
| 描述 | `banned_check`（取值 `checked`/`banned`/`pending`）在 `AD_SCHEMA` 中声明、在 `Ad` 模型中存储、全部素材均填写，但 **`src/compliance/` 从不读取它**（修复前）。语义后果：**标为 `'banned'` 的素材仍会通过全部 gate 被展示** |
| 影响 | 字段名与取值读起来像"已被标记为禁投"，实际零强制。这是审计中最容易被误读的落差——有人可能据此认为存在一层保护 |
| **处置（已执行，方案 A）** | 已在 compliance 管道实装第五步 `check_banned_check`：**仅 `'checked'` 放行**，`pending` 与 `banned` 一律 REJECT（fail-closed）。同步更新：`ADR-001`、`asr-register.md`、`invariants.md`、`concern-clusters.md`、`trace-matrix.md`、`architecture-blueprint.md`、`runtime-policy-catalog.md`、`AGENTS.md`、`requirements.yaml`。新增 6 项反例测试（含管道顺序契约测试） |
| **重开条件** | 已关闭。若未来决定改为方案 B（移除字段），须走 ADR（属 safety-critical 变更） |
| 负责人 | B + D |

---

**`TD-018`** — 门禁 1（测试批准）机制就绪但无真实批准记录；历史提交无法追溯满足

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt` + 流程缺口** |
| 来源 | `docs/test-approvals.yaml`；`docs/branch-protection.md` §6；`scripts/check_test_approval.py` |
| 描述 | 门禁 1 的载体（`docs/test-approvals.yaml`）与检查器已建立，但唯一记录 `TA-0001` 的 `approved_by` 仍是占位符，故被判定为**不可信的批准**。此外 **2026-09-30 的 4 次构建提交测试与实现同批产出**，课程要求的"实现前测试获批"**无法追溯满足** |
| 影响 | 现有一切测试（86 个）均不满足门禁 1 的"事前批准"要求；若现在提交 PR 修改测试文件，门禁 1 将**如实阻断**（这是正确行为，不是缺陷） |
| 补法 | ① 由**具名人类**在 `docs/test-approvals.yaml` 补一条真实批准记录（含 `req_ids` / `test_files` / `approved_by` / `approved_at` / `evidence`）；② 自生效起点（2026-10-06）起，所有新增/修改测试必须先有此记录 |
| **重开条件** | 下次修改测试文件之前。**历史缺口不可追溯修复**，仅登记并前向生效 |
| 负责人 | 人工（具名批准者） |

---

**`TD-019`** — 门禁 4（语义评估）不可用：评估集缺失且无 prompt 文件

| 字段 | 内容 |
|---|---|
| 分类 | **`evaluation debt`** |
| 来源 | `scripts/check_semantic_eval.py`；`README.md` 门禁表；`OQ-005` |
| 描述 | 门禁 4 要求"prompt/model 变更须先 replay 固定评估集过质量阈值"。但：① `eval/eval_cases.json` 尚未建立（口径待 `OQ-005`）；② 仓库当前**没有任何 prompt 文件**（`prompts/` 为空），因此门禁的触发条件本身不成立 |
| 影响 | 6 道门禁中唯一**无法实装**的一道。脚本已实现 fail-closed：一旦检测到 prompt/model 变更而评估集缺失，即**阻断**——但目前该路径从未被真正行使 |
| 补法 | ① 关闭 `OQ-005` 定评估集口径；② 建立 `eval/eval_cases.json`（≥20 条）+ `eval/eval_runner.py`；③ 在 `config.yaml` 声明质量阈值；④ P8 接入真实 LLM 后建立 `prompts/prompt_v1.0.yaml` |
| **重开条件** | P7（评估集）或 P8（真实 prompt）开始时 |
| 负责人 | D + B |
| **处置（已执行，2026-10-06）** | ✅ **已关闭**。`OQ-005` 已关闭（口径 = agent 自造 + 人类审查，阈值 0.95）；`eval/eval_cases.json` 建成 **25 条**（11 MUST_PASS / 14 MUST_FAIL）；`eval/eval_runner.py` 可一键 replay 并输出通过率 + 违规数 + p95；`config.yaml` 新增 `eval` 段（阈值单点来源）。**门禁 4 由此首次具备判据**。判定口径与分母分离的设计决策另立 `ADR-003`。 |

---

**`TD-020`** — **课程硬性要求的「真实 AI 组件」尚未实现**（`src/selector/` 为空）

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt` + 交付物缺口（D8）** |
| 来源 | `requirements.yaml` 的 `REQ-ADS-ARCH-002/003`、`REQ-ADS-AI-001/002`、`REQ-ADS-NFR-COST-001`；`architecture-blueprint.md` §4 元素 ④；本次 D8 核查 |
| 描述 | 课程开题即要求应用含**至少一个真实 AI 组件**（LLM 功能／检索管线／AI 决策路径）。本项目对应的组件是 **`src/selector/`（AI 建议层）**，但该目录**完全没有实现文件**。连带 `src/app/`（编排）、`src/render/`（输出）、`src/audit/`（证据）也全为空目录。**当前 `src/` 只实现了"确定性安全边界"那一半，没有"AI 组件"那一半。** |
| 影响 | ① **D8 的 fit criterion「full application source code」尚未满足**；② 系统**当前无法完成一次真实推荐**（无编排、无 AI 选择、无输出）；③ 课程的 AI 组件要求未落地。已实现部分（ads/scene/compliance）本身完整且有 86 项测试，但整体不成闭环 |
| 已就位、只差实现 | 该元素的**设计已完备**：`asr-register.md` 的 `ASR-ADS-04/14/A3-01/A3-02`、`invariants.md` 的 `INV-ADS-002/003/004/005/014`、`AGENTS.md` ④ 的 4 个模块文件与 ⑤ 的集成契约、`runtime-policy-catalog.md` 的 `RP-003`~`010` 均已就绪。**缺的是代码，不是设计。** |
| 补法 | 实现顺序 P4 `selector` → P5 `app` → P6 `render` + `audit`。**前置条件**：① 人工批准 ADR-001/002；② 关闭 `OQ-009`（"解释"的领域口径）；③ 关闭 `OQ-004`（置信度阈值）。三者未决前动工即返工 |
| **处置（已执行，2026-10-06）** | ✅ **已关闭**。三个前置条件全部满足（ADR-001/002 转为 `Accepted`，`OQ-004`/`OQ-009` 关闭），随后按 `docs/plans/P4-selector.md`（人类批准）实现 P4：`src/selector/` 已落地 6 个模块（`client` / `parser` / `context` / `explanation` / `types` / `__init__`），新增 3 个测试模块共 45 个测试。**课程开题的「至少一个真实 AI 组件」要求已满足。** |
| **重开条件** | 已关闭。剩余元素（`render`/`audit`/`app`）的缺口另立 `TD-022` |
| 负责人 | B（架构与 AI）+ C（应用与集成） |

---

**`TD-022`** — 元素 ⑤–⑦ 仍为空：系统**无法端到端跑通一次推荐**

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt` + 交付物缺口（D8）** |
| 来源 | `trace-matrix.md` §2.1；`architecture-blueprint.md` §4 元素 ⑤⑥⑦ |
| 描述 | P4 落地后，`src/` 已有 ①–④（素材/场景/合规/AI 建议层）。但 **`src/render/`（输出契约）、`src/audit/`（证据子系统）、`src/app/`（编排与降级路径）仍为空目录**。 |
| 影响 | ① **D8 的「full application source code」仍未满足**；② 系统**仍无法完成一次端到端推荐**——候选集与选择可用，但缺「编排 → 输出 → 证据」三段；③ 与之绑定的 10 条需求与 8 条不变量仍无测试证据（见 `acceptance-coverage-map.yaml`），含 `REQ-ADS-FR-003`（降级 no_ad）、`FR-004`（渲染）、`GOV-001`（审计）、`NFR-PERF-001`（超时四元素）、`SEC-001`（注入 gate） |
| 已就位、只差实现 | 三个元素的**设计已完备**：`AGENTS.md` ④ 的模块清单与 ⑤ 的集成契约、`runtime-policy-catalog.md` 的 `RP-001`~`017`（尤其 `RP-008`/`009` 的 fallback 与 timeout）、`trace-matrix.md` §1 的 **22 条运行时 monitor** 定义、`memory-design.md` §2 S1 的审计「只写不读」约束 |
| 补法 | P5 实现 `src/app/`（编排 + 6 条降级路径 + timeout gate + 阈值判定）→ P6 实现 `src/render/` + `src/audit/`（含 monitor 落地）。**自 `TD-001` 起，22 条 monitor 的落地主要落在此处。** |
| **重开条件** | 立即（P5 可开工：ADR 已批、OQ 已关，无剩余硬阻塞）。按 `Prompt.md` 的流程先出执行计划再实现 |
| 负责人 | C（应用与集成）+ D（证据与 monitor） |
| **处置（已执行，2026-10-06）** | ✅ **已关闭**。P5 实现 `src/app/`（编排 + 10 条降级路径 + timeout gate + 阈值判定 + 注入门 + 配置校验），P6 实现 `src/render/`（两形态 schema）与 `src/audit/`（JSONL 审计 + 22 条 monitor 登记）。**端到端已跑通**（`python -m app --time-slot night --device mobile --tag student` → 广告形态 + 审计记录）。新增 4 个测试模块共 85 个测试（套件 131 → 216）。 |

---

**`TD-023`** — P5/P6 的测试批准**晚于**实现（门禁 1 时序违规，如实保留）

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`（治理流程违规）** |
| 来源 | `docs/test-approvals.yaml` 的 **`TA-0003`**；`scripts/check_test_approval.py` |
| 描述 | 课程门禁 1 要求"测试在实现开始前获批"。P5/P6 的实现与测试**同批产出**（人类指示「P5，先跑通」，即优先端到端可运行），`TA-0003` 的 `approved_at` 因此**晚于**实现时间。这与 `TD-021` 的引导悖论不同：`TD-021` 是机制固有张力，本条是**主动接受的顺序倒置**。 |
| 影响 | 门禁 1 对本批测试将 **FAIL**（批准时间不早于实现开始）——**这是门禁在正确工作**，不是缺陷。 |
| 缓解（已做） | ① 在 `TA-0003` 中**显式标注为反例**，说明人类指示与倒置理由；② **不使用假的更早 `approved_at`** —— 伪造治理证据比留着缺口更糟；③ 本条目登记影响，供 D6 报告如实叙述。 |
| 补法 | 两条路，须人工选择：**(甲)** 接受为一次性例外并在 D6 报告中说明（理由是"人类明确要求先跑通"）；**(乙)** 对 P7/P8 **恢复"先批测试再实现"**，以证明流程可被遵守（更有说服力）。**建议 (乙)** —— 一次例外可解释，两次即成为习惯。 |
| **重开条件** | P7（评估集）或 P8（真实 LLM）开工前 |
| 负责人 | A（产品与流程）+ D（质量与治理） |

---

**`TD-024`** — `src/app/config.py` 不在 `AGENTS.md` ④ 的模块组织表内

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`（文档与实现漂移）** |
| 来源 | `AGENTS.md` ④ 模块组织表 vs 实际 `src/app/` 内容 |
| 描述 | `AGENTS.md` ④ 为 `src/app/` 声明了 3 个文件（`pipeline.py` / `sanitize.py` / `cli.py`），实际有 5 个：多出 `config.py`（配置加载与**启动期校验**，落地 `TD-006`）与 `__main__.py`（`python -m app` 入口）。 |
| 影响 | **S1 检查不受影响**（S1 是**包级**的：一个架构元素一个包；包内辅助文件不违规）。但**文档与实现存在不一致**：AGENTS.md ④ 声称的清单不再是完整的。这与"AGENTS.md 由架构工件装配而成"的前提冲突——如果实现可以有表外文件，该表的权威性就被削弱了。 |
| 补法 | 二选一：**(甲)** 更新 `AGENTS.md` ④ 补上这两个文件并说明其角色（推荐——它们是真实且必要的）；**(乙)** 把 `config.py` 并入 `pipeline.py`、`__main__.py` 的逻辑并入 `cli.py`。注意 `AGENTS.md` 变更须人工批准（它是 D3 交付物）。 |
| **重开条件** | 下次更新 `AGENTS.md` 时（与 D3 收尾一并做） |
| 负责人 | A（产品与流程）+ C（应用与集成） |
| **处置（已执行，2026-10-06，采方案甲）** | ✅ **已关闭**。随 `docs/plans/P7-eval.md` 批准一并处理：`AGENTS.md` ④ 补入 `src/app/config.py` 与 `src/app/__main__.py`，并加注"二者是 pipeline / cli 的**支撑文件**，不各自构成独立元素"；③ 权限表补入 `eval/` 与两个增量可改文件；① 的过时措辞（"剩余模块"）一并修正。**同时把 `eval/` 与 `scripts/mutation_check.py` 登记入表**，使 P7 新增顶层包不产生同类漂移。 |

---

**`TD-021`** — 门禁 1 的引导悖论：第一个测试不可能在第一个实现之前获批

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`（治理机制的固有张力）** |
| 来源 | `docs/test-approvals.yaml` 文件头说明；`scripts/check_test_approval.py` |
| 描述 | 门禁 1 要求"测试在实现开始前获批"。但本仓库的全部测试（86 个）都是**在批准机制建立之前**写成的，因此 `TA-0001` 的 `approved_at`（2026-10-06T14:00）**晚于** `test_banned_words.py` 的创建时间，时序上不满足该要求。<br>更深一层：**任何仓库的"第一个测试"都不可能满足此规则**——批准记录本身需要先存在，而测试文件也需要先存在才能被 `test_files` 引用。这是机制层面的固有张力，不是本项目的疏忽。 |
| 影响 | ① 历史上无法追溯合规（与 `TD-018` 同源）；② 门禁 1 在"变更集不含实现代码"时**退化为通过**（因无实现时间可比对），故当前不会阻断——但这意味着该门禁的**时序判定在无实现的 PR 上不生效**。这是刻意的宽松，避免文档类 PR 被误拦。 |
| 缓解（已做） | ① 悖论在 `test-approvals.yaml` 文件头、`branch-protection.md` §6 **显式声明，不掩盖**；② 门禁 1 对**此后新增**的测试严格前置批准（登记 → 批准 → 再实现）；③ `check_test_approval.py` 在批准者为占位符时**拒绝采信**该记录。 |
| 补法 | 无完全解法。可考虑的改进：把门禁 1 实现为"**测试文件必须先于实现文件出现在变更集中**"（比较两者的首次提交时间），而非依赖外部批准记录。该改进需在 D7 后续迭代中评估 |
| **重开条件** | 下次迭代门禁 1 的判定方式时 |
| 负责人 | D |

---

**`TD-025`** — 评估集无保护机制：改动它即可"让门禁变绿"

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`（治理闭环缺口）** |
| 来源 | `ADR-003` D7（评估集独立于被测系统演进）；`ADR-002` §2 D4 的受保护路径清单 |
| 描述 | `eval/eval_cases.json` 是门禁 4 的**判据来源**（`INV-ADS-016`），但它**不在** `ADR-002` D4 的"须 ADR"受保护路径清单中。因此：某人可以**删掉难例**或**放宽 `expected_ad_id`**，从而在不改实现的情况下让门禁通过 —— 门禁在形式上"生效"，实质上被绕过。 |
| 影响 | 这是"**用改判据的方式通过判据**"这一经典治理漏洞。当前无任何机械拦截；仅靠 `test_mutation_check.py` 的覆盖一致性检查间接约束（它不检查用例内容是否被削弱）。 |
| 缓解（已做） | ① 每条用例强制携带 `basis` + `anchors`（删改需留下理由）；② `test_eval_runner.py` 校验 ≥20 条硬门槛与结构完整性；③ 汇总计数由脚本核对，用例数下降会被发现（但**内容削弱**不会）。 |
| 补法 | **须人工决定**：把 `eval/` 加入受保护路径清单（改动须 ADR + 人工评审）。 |
| **处置（已执行，2026-10-06，方案甲）** | ✅ **已关闭**。人类在三方案中选择「**新建 `ADR-004`**」（符合 `ADR-002` 的冻结语义）。<br>· `ADR-004` D1 把**验证平面**的 **10 条**路径纳入受保护（`eval/` 2 条 + `scripts/` 6 条 + `acceptance-coverage-map.yaml` + 检查器）—— **不只 `eval/`**，因为审查发现同一漏洞模式波及整个验证平面。<br>· 受保护路径总数 **9 → 19**。<br>· `check_safety_paths.py` 改为**标记驱动的多 ADR 合并**（`ADR-002` 原文的路径表**一字未改**，仅加标记）。<br>· **已实测**：改 `eval/eval_cases.json` 无 ADR → **阻断**；附 `ADR-004` → **放行**。 |
| **残留** | 新立 `TD-028`（清单"忘放标记"是静默失败） |
| 负责人 | D（质量与治理）+ A（产品与流程） |

---

**`TD-026`** — Hook 只在 CI 生效，本地 pre-commit 未安装（存在绕过路径）

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`（强制机制覆盖不足）** |
| 来源 | `.opencode/permissions.jsonc` 的 `enforcement.hooks` H-001；`.opencode/rules.md` R5 |
| 描述 | 课程行 599 要求 **Permission 定义 WHO，Hook 强制 WHEN**。本项目的 hook 实现（`scripts/check_safety_paths.py`）目前**只在 CI 阶段**运行。因此存在绕过路径：本地直接修改 `data/*.json` 或 `src/compliance/` 并提交，**直到 CI 才被发现**。 |
| 影响 | safety-critical 变更的"必须附带 ADR"这一约束**不是前置的**，而是**滞后的**。滞后拦截仍比没有强，但不符合"hook 在事件发生时强制"的设计意图。 |
| 缓解（已做） | ① CI 阶段强制（已实测 FAIL 行为）；② `mcp-tool-manifest.md` §4 与 `.agent/rules.md` §5.3 **显式声明该局限**，不假装 hook 已完整；③ 分支保护文档给出 `enforce_admins` 等收紧手段（待管理员启用）。 |
| 补法 | 安装 `.git/hooks/pre-commit`（或 `.pre-commit-config.yaml`），调用 `check_safety_paths.py` 与 `check_ai_use_log.py`。**注**：`.git/hooks/` 不在版本控制内，故须同时提供**可复现的安装脚本**。 |
| **处置（部分执行，2026-10-06）** | ⚠️ **安装器已就位，hook 尚未安装**。已产出 `scripts/install_hooks.py`（含 `--check` / `--uninstall`，且**拒绝覆盖非本脚本安装的 hook**）。**但在 agent 会话中无法完成安装** —— 沙箱不允许子进程写入 `.git/hooks/`（实测 `PermissionError`）。<br>**须由你在自己的环境中执行一次**：<br>`python scripts/install_hooks.py`<br>之后可用 `--check` 验证（已安装时退出码 0）。<br>**当前状态**：`--check` 报"未安装"，即 safety-critical 拦截**仍只在 CI 阶段生效**。 |
| **重开条件** | 你执行安装脚本后即可关闭本条目 |
| 负责人 | D（质量与治理）+ **你（执行安装）** |

---

**`TD-027`** — "文档与实现一致"不可机械检验（上下文新鲜度只有流程、没有机制）

| 字段 | 内容 |
|---|---|
| 分类 | **`evaluation debt`** |
| 来源 | `.agent/rules.md` §5（context freshness —— 课程 D3 的公约要求） |
| 描述 | 课程要求"规则在需求变更后一个 sprint 内更新"。本项目**已定义** 8 项须同步的文件清单，但**没有任何机制检查它们是否真的同步了**。实证：已发生 **4 次漂移**（README 的"4 个空目录"、`AGENTS.md` ① 的"剩余模块"、blueprint §4 的"P7 待建"、`AGENTS.md` ④ 缺 2 个文件），**全部靠人工发现**。 |
| 影响 | 公约 §5 因此只能算**部分满足**。实际风险：评审读 README 会以为项目比实际落后（该项目已发生过）。 |
| 缓解（已做） | ① `.agent/rules.md` §5.1 给出 8 项清单；② §5.2 如实列出 4 次漂移作为"新鲜度不会自动维持"的证据；③ §5.3 把本条标为"未实现"而非宣称已保证；④ `fitness_functions.py` 的 TRACE 检查覆盖了其中一部分（追踪矩阵 ↔ 需求注册表）。 |
| 补法 | 写 `scripts/check_doc_freshness.py`，做**可机械判定的子集**：① `AGENTS.md` ④ 的文件清单 ↔ `src/` 实际文件（双向）；② `README.md` 交付物状态表 ↔ `trace-matrix.md` 的 Status 分布；③ blueprint §4 的"现状"列 ↔ 目录是否存在。**不可机械判定的部分**（如"措辞是否过时"）保持人工。 |
| **重开条件** | 下次文档同步时，或 **D6 报告写作时**（报告需要准确的现状描述） |
| 负责人 | D（质量与治理）+ A（产品与流程） |

---

**`TD-028`** — 受保护路径清单"忘放标记"是**静默失败**

| 字段 | 内容 |
|---|---|
| 分类 | **`guardrail debt`（新机制的脆弱点）** |
| 来源 | `ADR-004` D3/D4；`scripts/check_safety_paths.py` 的 `PATH_TABLE_MARKER_RE` |
| 描述 | `ADR-004` D3 规定了新增受保护路径的流程：新建 ADR → 放 `<!-- safety-critical-paths -->` 标记 → 紧随其后放路径表。但若某人**忘了放标记**（或标记前有别的标记行），该 ADR 的清单**不会生效**，且**不会有任何报错** —— 检查器只是"少合并了一份清单"，门禁静默变松。 |
| 影响 | 这是"机制依赖人工记得做某事"的典型脆弱点。**失败方向是危险的**：忘放标记 → 保护变少 → 无声。开发中已实测到该模式的**近亲**：`ADR-004` 的说明段里引用了标记字符串，朴素匹配把它当成了标记，导致清单被解析错（已用严格整行匹配修复）。这说明"标记识别"本身容易出错。 |
| 缓解（已做） | ① 改用**严格整行匹配**（`^\s*<marker>\s*$`）而非子串匹配；② `--show-paths` 打印**清单来源的 ADR 文件名**，忘放标记在人工审查中可见；③ `ADR-004` D3 把流程写清。 |
| 补法 | 让 `fitness_functions.py` 断言：**每份含路径表（首列为反引号路径）的 ADR 都必须带标记**。这样新增 ADR 忘放标记即 FAIL。 |
| **重开条件** | 下次新增受保护 ADR 时（或实现上述断言时） |
| 负责人 | D（质量与治理） |

---

## 2. 汇总

| 分类 | 条目 | 数量 |
|---|---|---|
| `guardrail debt` | `TD-001`、`002`、`004`、`006`、`007`、`008`、`014`、`017`、`018`、`021`、`023`、`024`、`025`、`026`、`028` | 15 |
| `evaluation debt` | `TD-003`、`009`、`010`、`015`、`016`、`019`、`027` | 7 |
| `human/cognitive debt` | `TD-005`、`011` | 2 |
| 工程整洁 | `TD-012` | 1 |
| 治理债（流程违规） | `TD-013` | 1 |
| **合计（含已关闭条目编号）** | | **28** |

> **状态统计（脚本核对）**：编号 `TD-001`~`TD-028` 共 28 条，**已关闭 7 条**
> （`TD-015` 部分、`TD-016` medical 死规则、`TD-019` 门禁 4 不可用、
> `TD-020` AI 组件缺失、`TD-022` 元素 ⑤–⑦ 为空、`TD-024` 模块表漂移、
> **`TD-025` 评估集无保护**）
> → **仍开放 21 条**。编号**不回收** —— 关闭的条目保留在册以便审计决策历史
> （与 `requirements.yaml` 的 `OQ` 关闭策略一致）。

**分类健康度**：本项目**没有** `prompt rot`、`hallucinated dependencies`、`untouchable code`、
`hidden dependencies`、`agent-induced bloat` 五类债务。

- 无 `prompt rot`：V1 尚无版本化运行时 prompt（`prompts/` 空）。
- 无 `hallucinated dependencies`：唯一运行时依赖 `jsonschema` 真实存在且被使用。
- 无 `untouchable code`：无冻结层（V1 forward build），全部代码可改。
- 无 `hidden dependencies`：模块间绝对导入，依赖关系由 `fitness_functions.py` 的 S1/S2 检查。
- 无 `agent-induced bloat`：`src/` 仅 11 个模块 7 个包。

> **债务不静默原则**：本表全部条目均有来源、影响与重开条件，无一条隐含。

---

## 3. 人工确认清单

| # | 待确认项 | 建议 | 状态 |
|---|---|---|---|
| 1 | 12 条债务的分类与优先级 | 维持 | ⏳ 待批 |
| 2 | `TD-007`（隐私）需在 `audit` 落地前定案 | 同意，优先级应提升 | ⏳ **需团队决策** |
| 3 | `TD-012` 需人工删除两个残留文件 | 提交前处理 | ⏳ 待办 |
| 4 | `TD-011`（角色分离）以何种方式满足 | 正式 CI 建立时定 | ⏳ 待批 |
