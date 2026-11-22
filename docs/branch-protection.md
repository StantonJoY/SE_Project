# 分支保护配置（Branch Protection）— D7 交付物

> **V3 状态（2026-11-22）**：V3 已通过 PR #3（merge commit `8b5a17a`）合入 `main`。
> 七道门禁（Gate 1/2/3/4/5/5b/6）已在 CI 中稳定运行；`.github/CODEOWNERS` 已落地。
> **`main` 仍未启用远端保护** —— 这是下一步唯一待办（§5）。
> ⚠️ 已知：Gate 1 在 V3 合并提交上为红（历史时序缺口，见 §6），**不影响**后续 PR 的判定。

> 课程 §6 原文：
> **"Branch protection: Branch protection must require passing CI, and changes to
> safety-critical paths must require human review with an accompanying architecture decision."**
>
> **状态**：配置说明 + 可执行命令清单 · 日期：2026-10-06
> **为什么是文档而不是代码**：分支保护是 **GitHub 仓库设置**，不是仓库内文件。
> 本文件给出「要设什么」与「怎么设」，由仓库管理员执行。

---

## 1. 必须满足的两条课程要求

| # | 要求 | 实现方式 |
|---|---|---|
| **BP-1** | 合并前必须通过 CI | 分支保护规则要求 status check 通过（`blocking-gates` 全部 job） |
| **BP-2** | **安全关键路径的改动必须人工评审，并附带架构决策** | ① `scripts/check_safety_paths.py` 机器强制"附带 ADR"；② CODEOWNERS 指定人工评审者；③ 禁止自行批准 |

---

## 2. 受保护路径清单（唯一来源）

**不在此处硬编码** —— 清单从 `docs/architecture/adr-002-fail-closed-and-governance.md` §2 D4 解析，
由 `scripts/check_safety_paths.py --show-paths` 输出。当前结果：

| 路径 | 强制 ADR？ |
|---|---|
| `src/compliance/` | ✅ 须 ADR |
| `src/ads/schema.py` | ✅ 须 ADR |
| `data/ads.json` | ✅ 须 ADR |
| `data/banned_words.json` | ✅ 须 ADR |
| `data/scene_rules.json` | ✅ 须 ADR |
| `docs/req/requirements.yaml` | ✅ 须 ADR |
| `src/selector/` | ✅ 改动阈值逻辑时须 ADR |
| `docs/architecture/invariants.md` | 只读（须人工评审） |
| `test/offline/` | 只读（不强制 ADR） |

> **设计要点**：清单源自 ADR，避免"分支保护配置"与"架构决策记录"两处漂移——
> 这是本项目从 `BUG-007` 学到的教训（同类规则分散在多处必然漂移）。

---

## 3. CODEOWNERS（已落地：`.github/CODEOWNERS`）

**设计目标是"文档好改、代码要审"**。GitHub **不支持按路径豁免评审**（评审要求是分支级、全有或全无），
因此用下面的组合模拟：

```
required_approving_review_count = 0     # 默认不需要批准
require_code_owner_reviews    = true    # 但被 CODEOWNERS 覆盖的路径需要 owner 批准
```

于是：

| 变更内容 | 结果 |
|---|---|
| 只改 `docs/`、`README.md`、`Report.md`（**未列入 CODEOWNERS**） | 只需过 CI，**不需要任何批准** |
| 改 `src/`、`data/`、`scripts/`、`eval/`、`test/`、`.github/`、`AGENTS.md`、blueprint | 需要所列 owner 之一批准 |

```text
/src/                        @StantonJoY @Synapse2002
/data/                       @StantonJoY @Synapse2002
/scripts/                    @StantonJoY @gaozhechun408-eng
/eval/                       @StantonJoY @gaozhechun408-eng
/test/                       @gaozhechun408-eng @StantonJoY
/.github/                    @StantonJoY
/AGENTS.md                   @StantonJoY
/architecture-blueprint.md   @StantonJoY
```

**刻意没有 `*` 通配**：`*` 会让所有路径都需要批准，文档 PR 就免不了签。

> **校准提示**：CODEOWNERS 里的账号若不在协作者列表中，GitHub **不会报错**，只会让该条规则静默失效。
> 启用保护前请确认这三个 handle 都在 `Settings → Collaborators` 里。
> 另：GitHub 不允许批准自己的 PR，改 `src/` 的 PR 必须由另一位 owner 批。

**注意**：CODEOWNERS 只强制"必须有人评审"，**不检查是否附带 ADR**——
后者由 `check_safety_paths.py` 在 CI 中强制。两者互补，与课程
「Permission 定义 WHO，Hook 强制 WHEN」的精神一致。

---

## 4. 所需 status checks（与 `ci.yml` 的 job 名一字不差）

| Job 名（`ci.yml`） | 对应课程门禁 |
|---|---|
| `Gate 1 · Test approval` | 门禁 1（测试批准） |
| `Gate 2 · Static analysis` | 门禁 2（ruff / mypy） |
| `Gate 3 · Schema (requirements registry)` | 门禁 3（需求登记册） |
| `Gate 4 · Semantic evaluation` | 门禁 4（语义评估 replay） |
| `Gate 5 · Regression (full offline suite)` | 门禁 5（全量离线回归） |
| `Gate 5b · Mutation verification` | 门禁 5b（变异验证） |
| `Gate 6 · AI-use log` | 门禁 6（AI 使用日志） |

> **Gate 1 建议晚一步再设为必需**：V3 合并提交上它是红的（历史时序缺口）。
> 对**新 PR** 而言，只要变更集里没有未获批的测试，它是会绿的（docs-only PR 直接 PASS）。
> 先跑通一次带前置批准的 PR（`TA-0005` 模式），再把 Gate 1 加进必需检查。

---

## 5. 设置方式

### 方式 A：GitHub 网页

`Settings → Branches → Add branch protection rule`

1. **Branch name pattern**：`main`
2. 勾选 **Require a pull request before merging**
   - **Require approvals**：`0` ← 关键：让文档 PR 不需要签
   - 勾选 **Dismiss stale pull request approvals when new commits are pushed**
   - 勾选 **Require review from Code Owners** ← 代码路径由 CODEOWNERS 兜住
3. 勾选 **Require status checks to pass before merging**
   - 勾选 **Require branches to be up to date before merging**
   - 逐个加入 6 个 check 名（**首次需先有一次 PR 运行过 CI，名称才会出现**）
   - ⬜ 暂不勾 `Gate 1 · Test approval`
4. 勾选 **Require conversation resolution before merging**
5. ⬜ **Do not allow bypassing the above settings** —— **先不勾**
   - 不勾 = 管理员可以直推 `main`（你可以在需要时直接推文档，也会绕过代码评审，属已知取舍）
   - 勾 = 管理员也不能直推，所有改动必须走 PR
6. ⬜ **Restrict who can push to matching branches** —— 暂不勾（勾了会把 admin 直推也关掉）
7. **Block force pushes / Prevent deletion**：保持勾选（默认阻止强推与删除）

**三种可选形态**（按你的偏好选）：

| 形态 | 文档怎么改 | 代码怎么改 | 代价 |
|---|---|---|---|
| **A. 推荐**：approvals=0 + Code Owners | 开 PR，过 CI 即可合（不需批准），或 admin 直推 | 必须 PR + 另一位 owner 批准 | 无 |
| B. 严格：approvals=1 + 不勾 bypass | 也要 1 个批准 | 必须 PR + 1 批准 + owner | 文档改动也要等人 |
| C. 仅 admin 直推：不勾 "Require a pull request" | 直推 | 直推（无评审） | 保护基本失效，不推荐 |

### 方式 B：`gh` CLI（需仓库管理员权限）

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/StantonJoY/SE_Project/branches/main/protection \
  -F "required_status_checks[strict]=true" \
  -F "required_status_checks[contexts][]=Gate 1 · Test approval" \
  -F "required_status_checks[contexts][]=Gate 2 · Static analysis" \
  -F "required_status_checks[contexts][]=Gate 3 · Schema (requirements registry)" \
  -F "required_status_checks[contexts][]=Gate 4 · Semantic evaluation" \
  -F "required_status_checks[contexts][]=Gate 5 · Regression (full offline suite)" \
  -F "required_status_checks[contexts][]=Gate 5b · Mutation verification" \
  -F "required_status_checks[contexts][]=Gate 6 · AI-use log" \
  -F "enforce_admins=true" \
  -F "required_pull_request_reviews[dismiss_stale_reviews]=true" \
  -F "required_pull_request_reviews[require_code_owner_reviews]=true" \
  -F "required_pull_request_reviews[required_approving_review_count]=1" \
  -F "restrictions=" \
  -F "allow_force_pushes=false" \
  -F "allow_deletions=false"
```

**校验是否生效**：

```bash
gh api /repos/StantonJoY/SE_Project/branches/main/protection \
  --jq '{checks: .required_status_checks.contexts, reviews: .required_pull_request_reviews.required_approving_review_count, admins: .enforce_admins.enabled}'
```

---

## 6. ⚠️ 诚实声明：本机制的生效起点与历史缺口

| 事实 | 说明 |
|---|---|
| **生效起点** | 分支保护与 6 道门禁于 **2026-10-06** 设计与落地，此前不存在；**7 道**（含 5b）自 2026-11-05 起 |
| **历史缺口** | 2026-09-30 的 4 次构建提交（`edac673` / `3ea7868` / `d85f910` / `d097d34`）**未经任何门禁**，且已直接进入 `main` |
| **门禁 1 不可追溯** | 该 4 次提交中测试与实现同批产出，**无法追溯满足**"实现前测试获批"；V2/V3 的测试同样如此（`TD-018`） |
| **本轮的补救** | `TA-0005`（2026-11-22）是**第一条真正的前置批准**（测试先写 → 批准 → 再实现）；`TA-0006` 对既有测试集作**事后验收**，不冒充前置批准 |
| **自批准问题** | 单人仓库下 `require_code_owner_reviews` 将导致**无法自行合并**；若团队只有一人有写权限，须显式接受此限制或增设第二名评审者 |

**处理方式**：本缺口**登记而不掩盖**，同时：
- 写入 `docs/debt-register.md`（`TD-018` 门禁 1 的历史缺口、`TD-013` 治理批次晚于首批实现）；
- 写入 `docs/ai-use-log.yaml`（`AIU-0002`~`AIU-0004` 的 notes）；
- 作为 **D6 报告的过程质量证据**（课程明确要求报告覆盖"工件如何共同演进"与
  "人工监督抓到什么 agent 没抓到的"——"发现治理顺序错了并补回"正是此类证据）。

> 课程把这种情形称为 **ADD-R 的触发条件**：测试证据暴露架构缺口时，**修订架构而非打补丁**。
> 本项目的处置即为一次 ADD-R：新增治理层（D3/D4/D7）而不改动既有代码基线。

---

## 7. 人工确认清单

| # | 待确认项 | 状态 |
|---|---|---|
| 1 | 是否启用 `enforce_admins`（管理员也受限） | ⏳ 待定（建议：先不勾，跑通 2 次 PR 后再勾） |
| 2 | CODEOWNERS 中的真实账号名 | ✅ 已写入 `@StantonJoY` / `@Synapse2002` / `@gaozhechun408-eng`，**需确认三者在协作者列表中** |
| 3 | 单人仓库下的评审者安排（见 §6 自批准问题） | ⏳ 待定：至少 1 名非作者协作者可批准 |
| 4 | 是否允许 force push（建议禁止） | ⏳ 待定（建议禁止） |
| 5 | Gate 1 是否立刻设为必需检查 | ⏳ 建议**先不设**，等一次带前置批准的 PR 走通后再设 |

---

## 8. 验证记录（保护是否真的生效）

> 保护是仓库设置，**不能只靠"我配了"来断言**。下表记录每次实测的时间、操作与实际结果。

| 日期 | 操作 | 预期 | 实际 |
|---|---|---|---|
| 2026-11-22 | 以仓库所有者身份**直推**包含本节的一次提交到 `main` | 若已勾 “Do not allow bypassing”：被拒；否则：成功 | 见 §8.1 |
| — | 只改 `docs/` 的 PR | 6 道 check 变绿后可合，无需批准 | 待做 |
| — | 改 `src/` 的 PR | 显示 “Review required from code owners”，需他人批准 | 待做 |

### 8.1 直推测试结果

（提交本节时同步填写；若直推被拒，本条会随 PR 一起合入。）
