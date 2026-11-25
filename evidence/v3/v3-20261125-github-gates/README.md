# GitHub 门禁实证（2026-11-25）

> 说明与拍摄要点见 [`docs/testing/V3-GitHub-Gate-Evidence.md`](../../../docs/testing/V3-GitHub-Gate-Evidence.md)。
> 本目录只放**三张图**，其余主张用文字描述（避免重复截图）。

| 文件 | 页面 | 覆盖的主张 |
|---|---|---|
| `1.png` | `Settings → Rules` 规则详情 | 规则存在；6 个 required checks 的具体名字；bypass list 含 owner；禁止 force push |
| `2.png` | PR #3（Checks + 合并区） | Gate 1 红 / 其余 6 道绿；合并状态；是否需要 Code Owner 评审 |
| `3.png` | Actions 运行列表 | 七道门禁是七个独立 job；0-job 旧 run 与 7-job 新 run 对照 |

## 命名

固定为 `1.png` / `2.png` / `3.png`（与说明文档 §4 一致）。补拍续图用 `3b.png` 这类后缀，不要重编号。

## 打码

截图内不得出现密钥、token、个人邮箱。遮挡用**纯色块**，不要用模糊（模糊可被还原）。

## 不截图的部分（文字说明在 docs 里）

| 主张 | 文字出处 |
|---|---|
| 直推被拒（开关前后对照） | `docs/branch-protection.md` §9.3 |
| 文档 PR 免评审 / 代码 PR 需 owner | `docs/branch-protection.md` §3 |
| job 耗时（变异 ~50 s、回归 ~30 s） | `evidence/v3/*/` 的 junit 与 stdout |

## 诚实边界

- `1.png` 的 bypass list 说明 owner 可绕过：规则约束其他成员，owner 豁免（已披露）。
- `2.png` 是"红着合入"的知情记录，不是"红着被拦"；拦截能力由直推被拒的日志证明。
- `3.png` 中 0-job 的根因是 workflow 级 `env` 引用 `runner.temp`，修复在 `8d9a14c`。
