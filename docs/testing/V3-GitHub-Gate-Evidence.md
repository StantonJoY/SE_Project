# GitHub 门禁实证：三张图 + 文字说明

> **归属**：D4 验证治理（CI/CD 证据）。截图存 `evidence/v3/v3-20261125-github-gates/`，
> 文字说明写在本文件，报告 §6.7 引用，`docs/review-memo.md` 的 PR #3 评审指向同一组图。
> 建立日期：2026-11-25 · 修订：**改为 3 张图**（三张已覆盖全部关键主张）

---

## 1. 为什么三张就够

12 个拍摄点里有大量重叠：规则页已经包含"哪 6 道 check"和"谁能绕过"；PR 页已经包含
"哪道红、合并是否被挡、是否需要评审"；Actions 页已经包含"几个 job、跑没跑、耗时多久"。

| 图 | 页面 | 一张图覆盖的主张 |
|---|---|---|
| **1.png** | `Settings → Rules`（规则详情展开） | 规则存在、目标分支 `main`、**6 个 required checks 的具体名字**、**bypass list 里有 owner**（解释了为什么 owner 仍能直推）、无 force push |
| **2.png** | PR #3 页面（Checks 区 + 底部合并区） | **Gate 1 红、其余 6 道绿**；合并按钮被挡（或"红着合入"的记录）；是否需要 Code Owner 评审 |
| **3.png** | Actions 运行列表（同屏含一次 0-job 的旧 run 与一次 7-job 的新 run） | 七道门禁是**七个独立 job**；曾经的"0 job 却显示成功"；修复后的真实执行 |

其余内容用文字描述，写在 §3。

---

## 2. 拍摄要点

**1.png · Ruleset**

- 展开规则的 required status checks，确认 6 个名字可见：
  `Gate 2 · Static analysis` / `Gate 3 · Schema (requirements registry)` /
  `Gate 4 · Semantic evaluation` / `Gate 5 · Regression (full offline suite)` /
  `Gate 5b · Mutation verification` / `Gate 6 · AI-use log`
- 同屏能看到 **Bypass list**（含 `StantonJoY`）——这是"诚实点"，主动展示比被问出来好
- 打码：仓库里的协作者邮箱、token 一律纯色块遮挡

**2.png · PR #3**

- 展开 Checks，让 **Gate 1 红 / 其余绿** 同屏
- 同屏看到底部合并状态（"Some checks were not successful" 或已合入的记录）
- 若页面显示 "Review required by code owners"，一并保留——它证明 CODEOWNERS 生效

**3.png · Actions**

- 优先让**历史与现状同屏**：上面一条 2026-10 的 run 显示 0 job，下面一条 2026-11 的 run 展开 7 个 job
- 若一屏放不下，两张截图拼成一张也可以（仍算 1 个文件）

---

## 3. 文字说明（截图不放的部分）

以下四条**不截图**，直接写在这里；报告与答辩引用本文件即可。

### 3.1 直推被拒（A3）

owner 在 bypass list 里，所以日常直推放行。开关前后对照是实测过的：

```
开启保护、无 bypass：
remote: - 6 of 6 required status checks are expected.
 ! [remote rejected] main -> main (push declined due to repository rule violations)

加入 owner 到 bypass list 后：
   52717b6..20d5856  main -> main      ← 成功（同样打印提示，但放行）
```

完整三段对照见 `docs/branch-protection.md` §9。**这是文字证据，不需要截图**。

### 3.2 文档 PR 免评审 / 代码 PR 需评审（A4 / A5）

这是 CODEOWNERS 的分支，不是两张独立页面：

- `.github/CODEOWNERS` 覆盖 `src/`、`data/`、`scripts/`、`eval/`、`test/`、`.github/`、
  `AGENTS.md`、blueprint；**`docs/` 刻意不列**；
- 分支保护设 `required_approving_review_count = 0` + `require_code_owner_reviews = true`。

于是：只改 `docs/` 的 PR → 无 owner → 不需要批准；改 `src/` 的 PR → 需要 owner 之一批准
（且不能是作者本人）。机制说明见 `docs/branch-protection.md` §3。

### 3.3 job 耗时（B2）

变异验证约 50 s（33 次注入，每次起一个 pytest 子进程），全量回归约 30 s（679 项），
其余四道合计约 20 s。这些数字在 `evidence/v3/*/` 的 junit 与 stdout 里有原始记录。

### 3.4 本地门禁与 CI 是同一套脚本

`ci.yml` 的 7 个 job 调用的是同一批 `scripts/check_*.py` 与 `pytest`，不是两套逻辑。
所以本地跑绿的判据与 CI 的判据一致（版本差异只体现在 Python 版本与依赖安装）。

---

## 4. 存放与引用

```
evidence/v3/v3-20261125-github-gates/
├── 1.png   规则页（required checks + bypass list）
├── 2.png   PR #3（Gate 1 红 / 其余绿 / 合并状态）
└── 3.png   Actions（0 job 旧 run 与 7 job 新 run 同屏）
```

引用位置：

| 位置 | 写法 |
|---|---|
| `Report.md` §6.7 末尾 | `Figures: evidence/v3/v3-20261125-github-gates/{1,2,3}.png` |
| `docs/review-memo.md` PR #3 评审 | "门禁实证见 …/1.png–3.png" |
| `docs/testing/V3-Test-Report.md` | 与已有 10 张验收截图并列 |

**图片不计入 10,000 词上限**，报告里可以放心引用。

---

## 5. 诚实边界

- 1.png 里的 bypass list 说明：**规则约束其他成员，owner 豁免**（有意为之，已在
  `Report.md` §6.7 与 `docs/branch-protection.md` §5 披露）；
- 2.png 展示的是"红着合入"的记录，不是"红着被拦"——V3 那一次是**知情决策**，
  门禁的拦截能力由 3.1 的直推被拒证明；
- 3.png 中 0-job 的根因是 workflow 级 `env` 引用了 `runner.temp`，修复提交 `8d9a14c`。
