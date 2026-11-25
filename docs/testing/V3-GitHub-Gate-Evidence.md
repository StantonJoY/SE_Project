# GitHub 门禁实证：截图清单与存放规范

> **目的**：证明"门禁真的拦过东西"，而不是"我们配置了门禁"。
> 课程第 6 问要的是"CI 如何**阻止**不合规变更被合并"——只有配置页不够，要有拦截证据。
> 建立日期：2026-11-25 · 对应报告 §6.1 / §6.7

---

## 1. 先分清三种证据（强度递增）

| 级别 | 证据 | 说明 | 强度 |
|---|---|---|---|
| C | 配置文件与设置页 | 证明"规则存在" | 弱——谁都能写 |
| B | CI 运行记录（红/绿、job 数、日志） | 证明"门禁在跑，且会红" | 中——需要真实失败 |
| **A** | **被拒绝的合并/推送** | 证明"门禁真的挡住了动作" | **强——这是课程要的** |

截图时**优先凑 A，其次 B，C 只作背景**。

---

## 2. 拍什么（按价值排序）

### A 级：拦截证据

| # | 页面 | 要截什么 | 证明 | 难度 |
|---|---|---|---|---|
| **A1** | PR #3 的 Checks 面板 | `Gate 1 · Test approval` **红**，其余 6 道绿 | 门禁会红、且红的是"测试未前置批准"这条 | 打开 PR 即可 |
| **A2** | PR #3 页面底部 | "Merging is blocked" 或 "Some checks were not successful" 的提示 | 红色检查**实际阻止了合并按钮** | 同上 |
| **A3** | 本地终端 | `git push origin main` 被拒：`push declined due to repository rule violations` + `6 of 6 required status checks are expected` | 直推被规则挡住（同一账号、同一命令，开关前后对照） | 需短暂移除 bypass 后重现（见 §4） |
| **A4** | 只改 `docs/` 的 PR | 6 道 check 绿 + **"No review required"** + 合并按钮可点 | 文档 PR 免批准（CODEOWNERS 未覆盖 `docs/`） | 开一个 PR |
| **A5** | 改 `src/` 的 PR | **"Review required"**（code owners）+ 合并按钮灰 | 代码路径必须 owner 批准 | 开一个 PR |

> A1/A2 是**现成的**——PR #3 就是带着 Gate 1 红合进去的。A3 需要 5 分钟重现。A4/A5 各开一个 PR，之后可关掉。

### B 级：门禁在跑

| # | 页面 | 要截什么 | 证明 |
|---|---|---|---|
| **B1** | `Actions` 运行列表 | 同一 run 内 **7 个 job**（Gate 1/2/3/4/5/5b/6） | 七道门禁不是一个脚本，是七个独立 job |
| **B2** | 任一 run 的 job 详情 | 步骤名 + 耗时（如变异验证 ~50 s、回归 ~30 s） | 门禁有真实成本，不是空壳 |
| **B3** | 历史 run 列表 | 2026-10-11 ~ 11-05 期间 **0 job** 的运行，与修复后的 7 job 对照 | 曾经的"绿色假象"与修复（报告 §6.2 的核心论据） |

> B3 是最有故事性的一张：**同一份 workflow，一边 0 job 显示"成功"，一边 7 job 真跑**。

### C 级：配置背景

| # | 页面 | 要截什么 |
|---|---|---|
| C1 | `Settings → Rules` | 规则名、目标分支 `main`、6 个 required checks、bypass list |
| C2 | `Settings → Branches` | 分支保护规则存在 |
| C3 | `Branches` 列表页 | `main` 旁的 **Protected** 徽章 |
| C4 | 仓库首页 `Insights → Pulse` 或 `Commits` | 提交/PR 活跃度（工作量证据，可选） |

---

## 3. 存放位置与命名

```
evidence/v3/v3-20261125-github-gates/
├── README.md                  ← 截图清单（本文件 §2 的表格，逐图一行）
├── A1-pr3-gate1-red.png
├── A2-pr3-merge-blocked.png
├── A3-direct-push-rejected.png
├── A4-docs-pr-no-review.png
├── A5-src-pr-review-required.png
├── B1-actions-7-jobs.png
├── B2-job-detail.png
├── B3-zero-jobs-vs-seven.png
└── C1-ruleset.png / C2-branch-protection.png / C3-branch-protected.png
```

命名规则：`<级别><序号>-<一句话>.png`。截图里**不要出现密钥、邮箱、token**；
需要打码时用纯色块，不要用模糊（模糊可被还原）。

---

## 4. A3 怎么重现（5 分钟，可逆）

管理员在 bypass list 里，所以正常直推是放行的。重现步骤：

1. `Settings → Rules → 你的规则 → Bypass list` → **临时移除** `StantonJoY`
2. 本地做一次无害提交（例如改一个文档里的错别字），`git commit`
3. `git push origin main` → 预期出现：

   ```
   remote: - 6 of 6 required status checks are expected.
    ! [remote rejected] main -> main (push declined due to repository rule violations)
   ```

4. **截图**（整段终端，含命令与被拒信息）
5. 回到 Settings，**把 `StantonJoY` 加回 bypass list**
6. 这次提交改走 PR（或 `git reset` 掉本地提交）

> 这一步做完，报告 §6.7 的三段对照表就有了三张实拍图：开启前成功 / 开启后被拒 / 加 bypass 后成功。

---

## 5. 截完怎么用

| 用在哪 | 怎么引 |
|---|---|
| `Report.md` §6.1 / §6.7 | 在表格下方加一行：`Evidence: evidence/v3/v3-20261125-github-gates/A1…A5` |
| `docs/testing/V3-Test-Report.md` | 在"门禁"一节加一行图片引用 |
| `docs/branch-protection.md` §9 | 已记录三段对照，把 A3 的图补到 §9.3 |
| 答辩 PPT | A1/A2/A3 三张按"红 → 被挡 → 被拒"顺序讲，30 秒讲完 |

**注意**：报告上限 10,000 词（不含图表）。截图是图片，**不计入词数**，可以放心放。

---

## 6. 诚实边界（写进 README，别等被问）

- A3 证明的是"规则对该账号生效"；因为 owner 在 bypass list，**日常直推仍然放行**。
  这条限制已写在 `Report.md` §6.7 与 `docs/branch-protection.md` §5。
- A4/A5 证明的是"CODEOWNERS 覆盖与否的差别"，不是"所有 PR 都被人工审过"。
- B3 只证明"当时 job 数为 0"，根因（workflow 级 `env` 引用 `runner.temp`）的修复在 `8d9a14c`。
