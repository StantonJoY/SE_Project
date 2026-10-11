# 分支保护配置（Branch Protection）— D7 交付物

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

## 3. CODEOWNERS（建议新增 `.github/CODEOWNERS`）

```
# 安全关键路径须指定人工评审者（课程 BP-2）
# 用法：把 @handle 替换为仓库中真实的人类账号。

# 默认所有路径需要评审
*                       @<team-lead>

# 安全关键路径
/src/compliance/        @<arch-owner> @<qa-owner>
/src/ads/schema.py      @<arch-owner>
/data/                  @<arch-owner> @<qa-owner>
/docs/req/              @<arch-owner> @<product-owner>
/docs/architecture/     @<arch-owner>
/architecture-blueprint.md  @<arch-owner>
```

**注意**：CODEOWNERS 只强制"必须有人评审"，**不检查是否附带 ADR**——
后者由 `check_safety_paths.py` 在 CI 中强制。两者互补，与课程
「Permission 定义 WHO，Hook 强制 WHEN」的精神一致。

---

## 4. 所需 status checks（与 `ci.yml` 的 job 名一致）

分支保护必须要求以下 6 个 check 通过：

| Job 名（`ci.yml`） | 对应课程门禁 |
|---|---|
| `Gate 1 · Test approval` | 门禁 1 |
| `Gate 2 · Static analysis` | 门禁 2 |
| `Gate 3 · Schema (requirements registry)` | 门禁 3 |
| `Gate 4 · Semantic evaluation` | 门禁 4 |
| `Gate 5 · Regression (full offline suite)` | 门禁 5 |
| `Gate 6 · AI-use log` | 门禁 6 |

---

## 5. 设置方式

### 方式 A：GitHub 网页

`Settings → Branches → Add branch protection rule`

1. **Branch name pattern**：`main`
2. 勾选 **Require a pull request before merging**
   - **Require approvals**：`1`（≥1 名人工评审者）
   - 勾选 **Dismiss stale pull request approvals when new commits are pushed**
   - 勾选 **Require review from Code Owners**
3. 勾选 **Require status checks to pass before merging**
   - 勾选 **Require branches to be up to date before merging**
   - 在搜索框中逐个加入上表 6 个 check 名（**首次需先有一次 PR 运行过 CI，名称才会出现**）
4. 勾选 **Require conversation resolution before merging**
5. 勾选 **Do not allow bypassing the above settings**（含管理员）
6. 勾选 **Restrict who can push to matching branches**（可选，推荐）

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
| **生效起点** | 分支保护与 6 道门禁于 **2026-10-06** 设计与落地，此前不存在 |
| **历史缺口** | 2026-09-30 的 4 次构建提交（`edac673` / `3ea7868` / `d85f910` / `d097d34`）**未经任何门禁**，且已直接进入 `main` |
| **门禁 1 不可追溯** | 该 4 次提交中测试与实现同批产出，**无法追溯满足**"实现前测试获批" |
| **门禁 4 尚未可用** | 固定评估集未建（口径待 `OQ-005`），且仓库当前无 prompt 文件 |
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
| 1 | 是否启用 `enforce_admins`（管理员也受限） | ⏳ 待定 |
| 2 | CODEOWNERS 中的真实账号名 | ⏳ **需你提供** |
| 3 | 单人仓库下的评审者安排（见 §6 自批准问题） | ⏳ **需你决定** |
| 4 | 是否允许 force push（建议禁止） | ⏳ 待定 |
