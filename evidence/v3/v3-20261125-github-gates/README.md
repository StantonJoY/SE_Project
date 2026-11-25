# GitHub 门禁实证（2026-11-25）

> 说明与引用位置见 [`docs/testing/V3-GitHub-Gate-Evidence.md`](../../../docs/testing/V3-GitHub-Gate-Evidence.md)。
> 本目录三张图，其余主张用文字描述。

| 文件 | 实际内容 | 覆盖的主张 |
|---|---|---|
| `1.png` | Pull requests 列表：Open 2 / Closed 16，两个 open PR 均显示 `6/7` + 红叉 | 门禁未全绿时 PR 停在 open、不可合并；历史上有 16 个 PR 走完流程 |
| `2.png` | Ruleset `main`：Enforcement **Active**、Target **Default**、Bypass **Repository admin / Always allow** | 规则存在且生效、作用于默认分支；owner 在 bypass 列表（有意为之） |
| `3.png` | 某 PR 的 Checks 弹层：**6 successful / 1 failing**，`Gate 5 · Regression` 失败 26s；Gate 1–4/5b/6 通过（12–23s） | 七道门禁是七个独立 job；门禁真的会红；docs-only 变更上 Gate 1 放行 |

## 命名

固定 `1.png` / `2.png` / `3.png`。补拍用 `3b.png` 这类后缀，不重编号。

## 打码

不得出现密钥、token、个人邮箱；遮挡用**纯色块**，不要模糊。

## 不截图的部分

| 主张 | 文字出处 |
|---|---|
| 直推被拒（开关前后对照） | `docs/branch-protection.md` §9.3 |
| 文档 PR 免评审 / 代码 PR 需 owner | `docs/branch-protection.md` §3 |
| 曾经的 0-job 运行 | 提交 `8d9a14c`；报告 §6.2 |
