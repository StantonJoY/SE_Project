# GitHub 门禁实证（2026-11-25）

> 截图清单与拍摄说明见 [`docs/testing/V3-GitHub-Gate-Evidence.md`](../../../docs/testing/V3-GitHub-Gate-Evidence.md)。
> 本目录只放截图；每张图对应一个 GitHub 页面与一条可核对的仓库主张。

## 清单

| 图 | 页面 | 证明 |
|---|---|---|
| A1 | PR #3 的 Checks 面板 | Gate 1 红、其余 6 道绿 |
| A2 | PR #3 页面底部 | 红色检查阻止了合并按钮 |
| A3 | 本地终端 | 直推被规则拒绝（开关前后对照） |
| A4 | 只改 `docs/` 的 PR | 文档 PR 免批准 |
| A5 | 改 `src/` 的 PR | 代码 PR 需 owner 批准 |
| B1 | Actions 某次 run | 同一 run 内 7 个 job |
| B2 | 某 job 详情 | 步骤与耗时（变异 ~50 s、回归 ~30 s） |
| B3 | 历史 run 对比 | 0 job 的"绿色假象" vs 修复后 7 job |
| C1 | Settings → Rules | 规则、目标分支、6 个 required checks、bypass list |
| C2 | Settings → Branches | 保护规则存在 |
| C3 | Branches 列表 | `main` 的 Protected 徽章 |

## 命名

`<级别><序号>-<一句话>.png`，例如 `A3-direct-push-rejected.png`。

## 打码

截图内不得出现密钥、token、个人邮箱。需要遮挡时用**纯色块**，不要用模糊（模糊可被还原）。

## 诚实边界

- A3 证明"规则对该账号生效"；owner 在 bypass list 中，**日常直推仍放行**（见 `Report.md` §6.7、`docs/branch-protection.md` §5）。
- A4/A5 证明"CODEOWNERS 覆盖与否的差别"，不证明"所有 PR 都被人工逐条审过"。
- B3 只证明"当时 job 数为 0"；根因（workflow 级 `env` 引用 `runner.temp`）的修复在提交 `8d9a14c`。
