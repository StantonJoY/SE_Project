# ADR-001：采用 Guarded Hybrid 架构（AI 解释，代码裁决）

> 课程对应：note 行 1213–1252（ADR 完整字段表）、行 1220–1232（ADR 示例）、行 5138–5142（Capstone ADR 评分量规）
> **状态**：**Accepted（已批准）** · 批准日期：**2026-10-06** · 批准者：**Shane**（具名人类）
> **日期**：2026-10-06 · **决策负责人**：B（架构与 AI 负责人）+ A（产品与流程负责人）
> **编号约定说明**：课程 VHIS 用 `docs/architecture/adr/00N-*.md` 子目录。本项目因工作区限制采用扁平文件
> `docs/architecture/adr-00N-*.md`，内容与字段完全对齐课程格式。ADR-001 = 被选方案。
>
> **批准记录**：人类于 2026-10-06 明确表示"看过了没问题，继续推进"，
> 据此将状态由 `Proposed` 变更为 `Accepted`。**No agent may self-approve**（课程 §11.3）——
> 本次变更由人类指令触发，非 agent 自批。
> **本 ADR 的冻结语义**：状态为 `Accepted` 后，`ADR-001` 进入**只读**；后续变更须走
> **修订**（新增 ADR 并引用本编号）或触发 §6 的重开条件，**不得直接改写本文**。

---

## 1. Context（问题或机会是什么）

系统需在给定场景特征（时段 / 设备 / 用户标签）与本地广告素材库下选出一条广告并渲染。
课程硬性要求应用**至少含一个真实 AI 组件**，且**至少有一个安全相关边界**，AI 输出必须被确定性代码约束。

候选方案的核心分歧点是：**谁来最终决定展示哪条广告**。

| 关切 | 冲突 |
|---|---|
| 语义灵活性 vs 确定性安全 | LLM 能理解"深夜加班"这类语义，但其输出是概率性的、可被注入影响 |
| 自动化吞吐 vs 合规责任 | 全自动最省人力，但广告展示有合规暴露面（违禁词、敏感品类、场景禁忌） |
| 上下文完整性 vs token 成本 | 候选集越大选择质量越高，但 token 成本与延迟上升 |

**架构驱动因子**（来自 `docs/req/requirements.yaml` 与 `docs/architecture/asr-register.md`）：
`REQ-ADS-NFR-SAFETY-001`（零逃逸，核心）、`REQ-ADS-ARCH-002`（闭集选择）、`REQ-ADS-ARCH-003`（输出 JSON）、
`REQ-ADS-SEC-001`（注入）、`REQ-ADS-GOV-001`（审计）。

---

## 2. Decision（我们决定做什么）

**采用 Guarded Hybrid：LLM 解释（advisory），确定性代码裁决（authoritative）。**

具体形态：

1. **LLM 只能在候选集内做闭集选择**，输出严格 schema 的 JSON（`ad_id` / `reason` / `confidence`）——**不得自创广告、不得输出候选集外的 ID**。
2. **确定性 compliance 管道位于 LLM 之后**，**五步**纯函数（`check_output` → `check_banned_words` → `check_banned_check` → `check_category` → `check_scene`），**任一失败即 REJECT**。
3. **解释路径与决策路径结构分离**：`reason` 是建议性输出，不得改写 `ad_id`，不得绕过 compliance。
4. **降级终点为 `no_ad`**（本项目无运行时人类复核环节，`no_ad` 即 fail-closed，见 ADR-002）。

```
场景特征 ──→ [预筛] 候选集 ──→ [LLM 闭集选择] ad_id/reason/confidence
                                      │
                                      ↓  (advisory)
                          [compliance 管道 · FINAL AUTHORITY]
                          output_exists → banned_words → banned_check → category → scene
                                      │
                        ┌─────────────┴─────────────┐
                     APPROVE                     REJECT
                        │                           │
                   渲染广告 + 解释            no_ad + 原因码
                        └──────────→ 审计证据（恰好 1 条）←──┘
```

---

## 3. Rationale（为什么这是最好选择）

对照课程 §2.2 的 Litmus Test（note 行 221）：本方案在 **S（结构）、QA（质量属性）、G（治理）、E（证据）** 四个维度上都显式落地，
而非把安全留给实现层去猜。

**评价准则（3 条，每维 W/M/S 打分）**：

| # | 准则 | Weak | Medium | Strong | 本方案 |
|---|---|---|---|---|---|
| C1 | **Invariant protection**（不变量保护） | 关键需求被违反或可被绕过 | 部分路径满足，需人工恢复 | **所有执行路径上确定性满足** | **Strong** |
| C2 | **Authority separation**（权威分离） | AI 输出直达最终结果 | 有门但可被绕过 | **结构性强制，无路径可绕** | **Strong** |
| C3 | **Complexity / Blast radius**（复杂度与爆炸半径） | 结构复杂、故障面大 | 中等 | **最简结构即可满足** | **Strong** |

> 课程行 1817：**一个没有可观察规则的准则不是准则，而是愿望。** 因此每条准则都给出可观察形式。

---

## 4. Alternatives（还考虑过哪些选项）

课程要求至少 3 条评价准则并记录被否选项的理由（note 行 5142、5150）。

### A1 — Raw Single-Agent（LLM 直接决定并展示）

| 维度 | 评估 |
|---|---|
| C1 Invariant protection | **Weak** — 无确定性强制，安全规则只能写在 prompt 里 |
| C2 Authority separation | **Weak** — 权威崩塌，AI 输出直达展示 |
| C3 Complexity | Strong |

**否决理由**：违反 `REQ-ADS-NFR-SAFETY-001`（零逃逸）与课程 ARCH-001（AI 非最终权威）。
prompt 是概率性的——**安全关键规则绝不写在 prompt 里**（note 行 1310）。
**永久否决**（本领域下无重新考虑条件）。

### A3 — Orchestrated Review-Rich（多 Agent + 运行时人类复核队列）

| 维度 | 评估 |
|---|---|
| C1 Invariant protection | Strong |
| C2 Authority separation | Strong |
| C3 Complexity | **Weak** — 需引入 checkpoint、评审队列、lease、幂等（对应课程 B3 harness 全套） |

**推迟（非否决）**：对 V1 基线过度工程化；且本项目 V1 无状态、单轮，引入复核队列会连带引入 State 维度。
**重新考虑条件**：业务要求"必须出广告"（即 `no_ad` 不可接受）时，或引入多轮上下文时。

---

## 5. Consequences（后果）

**收益（+）**

- 合规零逃逸**在结构上**成立，而非依赖模型自觉；`INV-ADS-001` 可在所有执行路径上判定 PASS/FAIL。
- 安全边界为纯函数 → **离线可测、可复现**（`REQ-ADS-ARCH-004`），无需真实 LLM 即可回归。
- LLM 可替换（供应商未定，OQ-001）而不影响安全主张——因为权威不在 LLM。
- 成本可控：闭集选择使 prompt 与输出都被 schema 约束（`REQ-ADS-NFR-COST-001`）。

**代价（−）**

- 需要维护 schema、合规规则表与证据格式三处契约，改动须走 ADR（安全关键路径）。
- **`no_ad` 是可选终态**：降级即无广告收入/无曝光。若业务不接受空广告位，本方案需回到 A3 重新评估（见 §6 触发器）。
- 闭集选择限制了"文案个性化"能力——V1 明确不做文案生成（`scope.out`）。
- 无运行时人类复核 → 异常只能靠**事后的审计证据 + 评估门**发现，不能当场拦截未知攻击。这是有意识的权衡。

---

## 6. Re-open Triggers（重新开启该 ADR 的条件，必须是可度量的）

| # | 触发条件 | 可度量形式 | 影响 |
|---|---|---|---|
| T1 | 合规逃逸 | `compliance_escape_count > 0` | **立即重开**；安全主张失效 |
| T2 | 引入"重试后展示次优候选" | 代码路径数 > 1 且展示发生在重试之后 | 使 `INV-ADS-003` 变为 fail-open |
| T3 | 引入自由文本用户输入 | 输入 schema 出现 `string` 自由字段 | `INV-ADS-005` sanitize gate 强度不足 |
| T4 | 引入多轮上下文 / 记忆 | 上下文层 4（HISTORY）由"不适用"变为适用 | `INV-ADS-014` compaction/re-injection 需重设 |
| T5 | 业务要求 `no_ad` 不可接受 | 无广告率超阈值 或 产品明确要求必出广告 | 需回到 A3（复核队列）或引入备选降级链 |
| T6 | LLM 供应商更换 | `model_id` 变更 | 重新标定 confidence 阈值与 token 预算；重跑评估集 |
| T7 | compliance 规则变更 | `scene_rules.json` / `banned_words.json` 变更 | 安全关键路径，须 ADR + 人工批准 |

---

## 7. Related Requirements

| REQ ID | 关系 |
|---|---|
| `REQ-ADS-NFR-SAFETY-001` | **核心驱动**：零逃逸，本决策的直接来源 |
| `REQ-ADS-ARCH-002` | 闭集选择（AI 非最终权威） |
| `REQ-ADS-ARCH-003` | 输出必须 schema 化 |
| `REQ-ADS-SEC-001` | pre-model sanitize gate |
| `REQ-ADS-GOV-001` | 审计证据 |
| `REQ-ADS-AI-001` | 解释路径隔离 |
| `REQ-ADS-FR-003` | 降级 no_ad |

---

## 8. Related Artifacts（链接代码、测试、配置、prompt、监控）

| 类型 | 具体构件 |
|---|---|
| 代码 | `src/compliance/pipeline.py`（FINAL AUTHORITY）、`src/ads/repository.py`（候选集）、`src/scene/parser.py` |
| 测试 | `test/offline/test_compliance.py`（12 项反例）、`test/offline/test_ads.py`、`test/offline/test_scene.py` |
| 配置 | `config.yaml`（`selector.confidence_threshold`、`llm.timeout_sec`） |
| 数据 | `data/ads.json`、`data/banned_words.json`、`data/scene_rules.json` |
| 架构工件 | `docs/architecture/asr-register.md`（`ASR-ADS-04`）、`docs/architecture/invariants.md`（`INV-ADS-001`） |
| 监控 | 待建：p95 延迟、合规逃逸计数、降级原因码分布（`docs/architecture/trace-matrix.md`） |

---

## 9. 架构设计过程记录（课程要求呈现 process）

1. **输入重估**：先按课程 A1 对 20 条 RE 需求做五维 Litmus 判定 → 16 ASR + 4 impl（`asr-register.md` §1）。
2. **架构性判定**：`REQ-ADS-NFR-SAFETY-001` 命中 3/5 维 → 判定为**核心 ASR**，强制 deterministic wrapper。
3. **候选生成**：基于 concern cluster 生成 3 个候选（A1 Raw / A2 Guarded Hybrid / A3 Orchestrated）。
4. **准则打分**：用 C1/C2/C3 三维 W/M/S 打分（§3–§4）。
5. **决策**：A2 在 C1、C2 上 Strong 且 C3 最简 → 选定。
6. **形式化**：A2 不变量形式化为 `INV-ADS-001`（六字段齐全，含 fail-closed fallback）。
7. **人工闸门**：本 ADR 状态为 **Proposed**，须人工批准后方可视为 Accepted（课程行 3830：计划获批前不得产出代码）。
