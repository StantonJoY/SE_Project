# GitHub 门禁实证：三张图 + 文字说明

> **归属**：D4 验证治理（CI/CD 证据）。截图存 `evidence/v3/v3-20261125-github-gates/`，
> 文字说明写在本文件，报告 §6.7 引用。
> 建立 2026-11-25 · 修订 2026-11-25（**按实际截图内容改写**，此前描述与图不符）

---

## 1. 三张图分别是什么

### 1.png · PR 列表：门禁未全绿时 PR 停在 open

可见内容：

- 顶部筛选 `is:pr state:open`，结果 **Open 2 / Closed 16**——历史上已有 16 个 PR 走完流程；
- 两个仍 open 的 PR 都带 **`6/7` + 红色叉**：
  - `#6 docs(v2): complete delivery documentation and evidence index`（Collaborator，昨天开）
  - `#1 V2: 确定性竞价、预算结算与 CI 修复`（Collaborator，上周开）

**证明**：PR 的合并状态与检查结果绑定显示；只要 7 道里有 1 道未过，PR 就不会显示为可合并。

### 2.png · Ruleset `main`：规则存在、生效、且有 bypass

可见内容：

| 字段 | 值 |
|---|---|
| Ruleset Name | `main` |
| Enforcement status | **Active** |
| Bypass list | **Repository admin**（Roles）· `Always allow` |
| Target branches | **Default**（默认分支，即 `main`） |

**证明**：规则是"启用"状态、作用于默认分支；**管理员角色在 bypass 列表里**——
这就是 owner 仍能直推的原因，属有意设计（见 `Report.md` §6.7、`docs/branch-protection.md` §5）。

### 3.png · 某 PR 的 Checks 弹层：6 绿 1 红，合并被挡

可见内容：

- 标题：**Some checks were not successful** — *6 successful and 1 failing checks*
- 失败项：**`Gate 5 · Regression (full offline suite)` — Failing after 26s**
- 通过项与耗时：`Gate 1 · Test approval` 12s、`Gate 2 · Static analysis` 17s、
  `Gate 3 · Schema (requirements registry)` 14s、`Gate 4 · Semantic evaluation` 17s、
  `Gate 5b · Mutation verification` 23s、`Gate 6 · AI-use log` 16s

**证明**（三点，全部来自这一张图）：

1. **七道门禁是七个独立 job**，各自有独立耗时（12–26 s），不是一个脚本包了个壳；
2. **门禁真的会红**，而且红色项直接决定 PR 不可合并；
3. **Gate 1 在 docs-only 变更上是通过的**（12 s）——这正好印证"文档改动不需要测试批准"的设计：
   `Gate 1` 只对"变更集里含未获批测试"的 PR 拦，docs PR 自然放行。

> 注：失败的是 `Gate 5`（全量回归），不是 `Gate 1`。这与设计一致——
> 该 PR 改的是文档，但回归套件仍须全绿，否则一样不能合。

---

## 2. 三张图没覆盖的部分（文字说明）

### 2.1 直推被拒

owner 在 bypass 列表里，日常直推放行；开关前后对照是实测过的：

```
开启保护、无 bypass：
remote: - 6 of 6 required status checks are expected.
 ! [remote rejected] main -> main (push declined due to repository rule violations)

把 owner 加入 bypass 列表之后：
   52717b6..20d5856  main -> main      ← 成功（提示仍在，放行）
```

完整三段对照见 `docs/branch-protection.md` §9。

### 2.2 文档 PR 免评审 / 代码 PR 需评审

这是 `CODEOWNERS` 的分支，不是两个独立页面：

- `.github/CODEOWNERS` 覆盖 `src/`、`data/`、`scripts/`、`eval/`、`test/`、`.github/`、
  `AGENTS.md`、blueprint；**`docs/` 刻意不列**；
- 分支保护设 `required_approving_review_count = 0` + `require_code_owner_reviews = true`。

结果：只改 `docs/` 的 PR 不需要批准（仍需过 CI）；改 `src/` 的 PR 需 owner 之一批准，
且不能是作者本人。机制说明见 `docs/branch-protection.md` §3。

### 2.3 曾经的"0 job 却显示成功"

2026-10-11 → 11-05 期间，CI 运行显示完成但 **0 个 job**，根因是 workflow 级 `env` 引用了
`runner.temp`；修复提交 `8d9a14c` 之后 7 个 job 才真正注册。这一段用提交与运行记录说明，
未单独截图（`3.png` 已展示修复后的七道 job 及耗时）。

### 2.4 本地门禁与 CI 是同一套脚本

`ci.yml` 的 7 个 job 调用的就是 `scripts/check_*.py` 与 `pytest` 本身，不是两套逻辑；
因此本地跑绿与 CI 跑绿的判据一致。

---

## 3. 引用位置

| 位置 | 写法 |
|---|---|
| `Report.md` §6.7 | `Figures: evidence/v3/v3-20261125-github-gates/{1,2,3}.png` |
| `docs/review-memo.md` PR #3 评审 | 门禁实证见本目录 1–3.png |
| `docs/testing/V3-Test-Report.md` | 与已验收的 10 张截图并列 |

**图片不计入 10,000 词上限。**

---

## 4. 诚实边界

- `1.png` 中的两个 open PR 至今未合入，原因是 `6/7`（具体失败项见 `3.png`）；
- `2.png` 的 bypass 列表说明 **owner 可绕过**：规则约束其他成员，owner 豁免，已在报告 §6.7 披露；
- `3.png` 展示的是"红着**不能**合"的当前状态；历史上有一次"红着合入"（PR #3，知情决策，
  见 `review-memo.md` 的 PR #3 评审条件），两者不冲突。
