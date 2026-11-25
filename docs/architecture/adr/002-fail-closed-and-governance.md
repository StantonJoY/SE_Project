# ADR-002：Fail-Closed 终态、证据不可协商与失败归因治理

> 课程对应：note 行 1713（fail-closed vs fail-open）、行 538（audit 不可协商）、行 4229/4241–4249（失败归因 decision gate）、行 1464–1479（Permission Model）
> **状态**：**Accepted（已批准）** · 批准日期：**2026-10-06** · 批准者：**Shane**（具名人类）
> **日期**：2026-10-06 · **决策负责人**：D（质量与治理负责人）+ B（架构与 AI 负责人）
> **依赖**：ADR-001（Guarded Hybrid，同日已 `Accepted`）给出的权威边界。本 ADR 细化其运行期失败语义与变更治理。
>
> **批准记录**：人类于 2026-10-06 明确表示"看过了没问题，继续推进"。
> **No agent may self-approve**（课程 §11.3）——本次变更由人类指令触发，非 agent 自批。
> **冻结语义**：状态为 `Accepted` 后本 ADR 进入**只读**；后续变更须走修订（新增 ADR）或触发 §6 重开条件。

---

## 1. Context

ADR-001 确立了"AI 建议、代码裁决"，但留下四个未定义问题，全部属治理与证据范畴：

| # | 未定义问题 | 若不定义的后果 |
|---|---|---|
| Q1 | 无运行时人类复核时，降级的**终态**是什么 | 无法判定降级是否安全（fail-open 风险） |
| Q2 | 审计写入失败时系统怎么办 | 可能出现无证据的决策（违反 GOV-001） |
| Q3 | 测试失败后，改代码还是改架构 | 静默 patch 掩盖架构缺口（课程明确点名的违规） |
| Q4 | 谁可以改 safety-critical 文件、如何拦截 | 权限只声明不强制（Permission ≠ enforcement） |

---

## 2. Decision

### D1 — 降级终态为 `no_ad`（fail-closed）

本项目**没有运行时人类复核环节**，因此不存在 VHIS 的 `REVIEW` 终态。降级终点统一为 **`no_ad`**（不展示任何广告）。

| VHIS | 本项目 | fail-closed？ |
|---|---|---|
| `REVIEW`（转人工） | **`no_ad`（不出广告）** | ✅ 等价——不展示即不产生合规暴露面 |
| `REVIEW` + checkpoint（人工稍后处理） | 无对应物 | ⚠️ 见风险 R-001 |

**重试不构成 fail-open 的说明**：`INV-ADS-003`（非法 JSON）含"重试 1 次"。重试**发生在任何展示之前**，
且只推迟终态、不改变终态（终态仍是 `no_ad`）；重试期间无任何广告被展示。因此该路径**不构成 fail-open**。
若未来引入"重试后展示次优候选"，**即变为 fail-open，必须重开 ADR-001**（触发器 T2）。

### D2 — 审计不可协商：写入失败即整体失败

课程行 538 明确 **audit logging 不可协商（GOV-001），token 节省不能绕过它**。因此：

**审计写入失败 → 本次推荐失败（fail-closed），不静默继续。**

这是**有意牺牲可用性换取证据完整性**的权衡。理由：无法审计的决策等于无证据决策，
在任何争议或合规审查中都不可辩护。

### D3 — 失败归因：绝不静默 patch 代替架构修订

课程行 4241–4249 的分类门槛：

| 现象 | 归因 | 正确动作 |
|---|---|---|
| agent 违反架构约束 | Code Bug | 修代码 |
| agent 遵守每条约束、结构测试通过、**行为/质量测试失败** | **架构 UNDERSPECIFIED** | **改架构（ADD-R），不要 patch 代码** |

> 课程行 4229：**The code is CORRECT. The architecture is UNDERSPECIFIED.**

落实到本项目：**为修复不变量违规而修改 safety-critical 代码时，必须先有 ADR 与工件更新**（`INV-ADS-009`）。

### D4 — 权限与钩子双机制

课程行 599：**Permission 定义 WHO，Hook 强制 WHEN；两者都需要，单独任何一个都不够。**

| 机制 | 范围 | 作用 | 触发 |
|---|---|---|---|
| **Permission** | 宽范围 | 角色级访问控制：声明谁可写哪些路径 | 始终强制 |
| **Hook** | 事件特定 | pre-commit 拦截 safety-critical 路径的无 ADR 变更 | 仅变更时触发 |

**safety-critical 路径清单**（本项目）：

<!-- safety-critical-paths -->
<!-- 本标记由 scripts/check_safety_paths.py 识别：其后的第一张表即受保护路径清单。
     清单的**补充**由后续 ADR 承载（如 ADR-004 加入 eval/），本表保持冻结原文 ——
     见下方「清单的演进」说明。 -->

| 路径 | Plan Agent | Build Agent | 人工必须？ |
|---|---|---|---|
| `src/compliance/` | Read | **No access** | **是 — 须 ADR** |
| `src/ads/schema.py` | Read | **No access** | **是 — 须 ADR** |
| `data/ads.json` | Read | **No access** | **是 — 须 ADR**（素材契约与 `banned_check`/`scene_restrictions` 的载体） |
| `data/banned_words.json`、`data/scene_rules.json` | Read | **No access** | **是 — 须 ADR** |
| `docs/architecture/invariants.md` | Read/Write | Read | **是** |
| `docs/req/requirements.yaml` | Read/Write | Read | **是 — 须 ADR** |
| `test/offline/` | Read | Read/Write | 否 |
| `src/selector/` | Read | Write（guarded） | 改动阈值逻辑时须 ADR |

---

## 3. Rationale

1. **降级必须方向确定**：课程行 1713——`REVIEW` 是 fail-closed，`retry` 是 fail-open，
   **在受监管系统中 fail-closed 是唯一安全默认**。`no_ad` 在本项目语境下是 `REVIEW` 的等价物。
2. **证据是治理的地基**：课程 §4.7 把"可解释性"定义为**架构需求而非 UI 特性**，且要求每个决策点设计出审计证据。
3. **失败归因决定会不会腐化**：若测试失败就改代码，架构缺口会被永久掩盖（课程行 3547：必须修订架构，而不是给代码打补丁）。
4. **只声明权限等于不拦截**：课程行 1479——**Permission ≠ Trust, it is enforcement.**

---

## 4. Alternatives

| 备选 | 否决/推迟理由 |
|---|---|
| **A. 降级返回"最安全的候选"**（仍有广告展示） | **fail-open**：仍会展示未通过全部 gate 的内容。**永久否决** |
| **B. 审计失败时告警但继续推荐** | 产生无证据决策；违反 GOV-001 零容忍条款。**永久否决**（除非 T-3 触发并改为同步阻塞队列） |
| **C. 只用权限文件、不建 hook** | 只声明不拦截；违反课程 GOV-002 的"两种机制都需要"。**永久否决** |
| **D. 引入运行时人工复核队列** | 需引入 checkpoint/queue/lease（B3 harness 全套），对 V1 过度工程化。**推迟**（与 ADR-001 A3 同条件重开） |

---

## 5. Consequences

**收益（+）**
- 降级语义唯一确定，可判定 PASS/FAIL，无解释空间。
- 任何一次决策都可辩护（证据完整，恰好 1 条）。
- 架构缺口不会被静默 patch 掩盖，治理可审计。
- safety-critical 路径有机制级保护，而非依赖约定。

**代价（−）**
- **可用性风险**：审计存储故障时推荐服务整体不可用（见 R-005）。
- **无广告位风险**：`no_ad` 会产出空广告位（业务上可能不可接受，见 T5）。
- 权限 + hook 双机制带来工程成本（`.opencode/permissions.jsonc` + pre-commit 脚本）。
- 失败归因要求每次行为测试失败都产出 ADR，流程较重。

---

## 6. Re-open Triggers

| # | 触发条件 | 可度量形式 |
|---|---|---|
| T-1 | 业务要求 `no_ad` 不可接受 | 无广告率超阈值 或 产品明确要求必出广告 |
| T-2 | 引入运行时人类复核 | 出现 checkpoint / 评审队列元素 |
| T-3 | 审计改为异步或可延迟 | 审计写入失败率 > 阈值且业务接受"延迟补账" |
| T-4 | 引入"重试后展示次优候选" | 展示发生在重试之后的代码路径数 > 0 |
| T-5 | safety-critical 路径清单变更 | `src/` 或 `data/` 下新增受保护路径 |
| T-6 | 权限模型被绕过的事件发生 | `permission_bypass_count > 0` → 立即重开 |

---

## 7. Related Requirements

| REQ ID | 关系 |
|---|---|
| `REQ-ADS-GOV-001` | D2 审计不可协商 |
| `REQ-ADS-GOV-002` | D4 权限 + hook |
| `REQ-ADS-FR-003` | D1 降级终态 |
| `REQ-ADS-NFR-PERF-001` | D1 超时 fallback |
| `REQ-ADS-AI-002` | D3 证据捕获 + 结构性拦截 |
| `REQ-ADS-NFR-QA-002` | D3 验证完整性（流程不变量） |

**相关不变量**：`INV-ADS-009`、`INV-ADS-010`、`INV-ADS-011`、`INV-ADS-012`、`INV-ADS-013`。

---

## 8. Related Artifacts

| 类型 | 具体构件 |
|---|---|
| 架构工件 | `docs/architecture/invariants.md`（§1 fail-closed 声明）、`docs/architecture/asr-register.md`（`ASR-ADS-09/11/13`） |
| 待建工件 | `.opencode/permissions.jsonc`、pre-commit hook、`docs/architecture/runtime-policy-catalog.md`、`docs/debt-register.md` |
| 代码 | `src/app/`（fallback path，P5 待建）、`src/audit/`（P6 待建） |
| 配置 | `config.yaml`（`llm.timeout_sec`） |
