# CS5351 V1 Mock / Offline 截图演示

## 1. 演示信息

- 项目：场景化广告推荐引擎
- 版本：V1
- Commit：`a31860fc3fb7c0710cf2d7ed157d3ebab2dafe77`
- 运行 ID：`v1-20261104-a31860f-02`
- 测试模式：Mock
- 演示方式：终端截图 + 原始日志
- 演示日期：2026-11-05

## 2. 演示范围

本次演示覆盖：

- 正常广告推荐
- 非法场景结构化降级
- 确定性合规过滤
- 固定评估集
- 审计记录与版本溯源
- 离线测试
- 静态检查
- 仓库完整性

本次演示不覆盖：

- 真实 LLM API
- live 测试
- 真实模型语义质量
- 真实模型在线延迟
- `prompts/` 和 `test/live/`

## 3. 截图清单

保存目录：

`evidence/v1/v1-20261104-a31860f-02/07-demo/screenshots/`

| 编号 | 文件名                         | 展示内容                          |
| ---- | ------------------------------ | --------------------------------- |
| 01   | `01-environment.png`           | Git commit、Python、源码路径      |
| 02   | `02-tests.png`                 | 299 个离线测试通过                |
| 03   | `03-normal-recommendation.png` | 正常推荐结果                      |
| 04   | `04-audit-record.png`          | 审计字段与五步合规                |
| 05   | `05-invalid-input.png`         | 非法场景降级                      |
| 06   | `06-eval-summary.png`          | 固定评估集通过                    |
| 07   | `07-safety-refusals.png`       | 敏感品类和场景规则拒绝            |
| 08   | `08-static-checks.png`         | Ruff、mypy、依赖、Schema、fitness |
| 09   | `09-repo-and-evidence.png`     | 仓库完整性、manifest、checksums   |
| 10   | `10-limitations.png`           | Gate 1、Gate 6 和真实 LLM 限制    |

## 4. 截图规则

- 使用完整终端窗口截图。
- 每张截图必须能看到命令和结果。
- 字体保持清晰可读。
- 不展示 API key、token、密码或个人信息。
- 截图不能修改原始输出。
- 每张截图必须与 evidence 目录中的文本日志对应。

## 5. 演示结论

- Mock / Offline 测试范围：PASS WITH LIMITATIONS
- 完整课程 V1 交付：CHANGES REQUIRED