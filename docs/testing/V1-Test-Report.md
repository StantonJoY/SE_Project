# CS5351 V1 Mock / Offline 测试报告

## 1. 报告状态

- 报告状态：PASS WITH LIMITATIONS
- 课程交付准备度：CHANGES REQUIRED
- 运行 ID：`v1-20261104-a31860f-02`
- 测试模式：Mock
- 测试范围：V1 deterministic offline/mock validation
- 测试日期：2026-11-04 至 2026-11-05

## 2. 测试基线

| 项目                      | 值                                         |
| ------------------------- | ------------------------------------------ |
| GitHub 仓库               | `git@github.com:StantonJoY/SE_Project.git` |
| 本地测试目录              | `E:\cityu\SE\project\SE_Project-test`      |
| 分支                      | `test/v1-candidate-a31860f`                |
| Commit                    | `a31860fc3fb7c0710cf2d7ed157d3ebab2dafe77` |
| V1 commit 人工确认        | PENDING                                    |
| Python                    | 3.11.17                                    |
| Conda 环境                | `SEProject`                                |
| Editable project location | `E:\cityu\SE\project\SE_Project-test`      |

## 3. 测试范围

本次测试覆盖：

- 正常推荐路径
- 非法场景与参数错误
- 配置和数据文件缺失
- MockLLM 建议层
- 五步确定性合规管道
- 低置信度、畸形输出、超时和不可用降级
- 注入检测
- 审计记录与版本溯源
- 299 个 offline 测试
- 25 条固定评估集 replay
- Ruff、mypy、依赖、Schema、fitness
- 仓库完整性检查
- 部分课程阻塞门禁

本次测试不覆盖：

- 真实 LLM client
- live 测试
- 真实模型语义质量
- 真实 API 延迟、鉴权、限流和网络故障
- `test/live/` 和 `prompts/`

## 4. 执行结果

| 检查项                     | 结果                                                         | 证据                                            |
| -------------------------- | ------------------------------------------------------------ | ----------------------------------------------- |
| 测试收集                   | PASS，299 个测试                                             | `pytest-collect.*`                              |
| 全量 offline 回归          | PASS，299 passed                                             | `offline-tests.stdout.txt`、`offline.junit.xml` |
| 正常推荐                   | PASS，`ad_001`                                               | `normal-03.*`                                   |
| 非法场景                   | PASS，`no_ad / scene_invalid`                                | `invalid-02.*`                                  |
| 非法配置                   | PASS，退出码 2                                               | `invalid-config.stderr.txt`                     |
| 素材缺失                   | PASS，退出码 2                                               | `missing-data.stderr.txt`                       |
| 固定评估集                 | PASS，11/11 + 14/14，违规 0                                  | `eval-replay.json`                              |
| Ruff                       | PASS                                                         | `ruff.stdout.txt`                               |
| mypy                       | PASS，32 source files                                        | `mypy.stdout.txt`                               |
| 依赖检查                   | PASS                                                         | `dependencies.stdout.txt`                       |
| Schema                     | PASS                                                         | `schema.stdout.txt`                             |
| Fitness                    | PASS                                                         | `fitness.stdout.txt`                            |
| 实现一致性审计             | PASS，0 发现 / 48 通过                                       | `implementation-audit-02.stdout.txt`            |
| 仓库完整性                 | PASS                                                         | `repo-completeness.stdout.txt`                  |
| 审计字段与溯源             | PASS                                                         | `normal-03.audit.jsonl`                         |
| 变异验证                   | PARTIAL，12 条有效，1 条假阳性                               | `mutation-check.stdout.txt`                     |
| Gate 1 Test approval       | 当前 Run 02 工作区修改：Gate 1 PASS。 V1 基线提交 a31860f：Gate 1 历史缺口仍为 OPEN。 | `test-approval-explicit.stdout.txt`             |
| Gate 4 Semantic evaluation | PASS，不适用                                                 | `semantic-eval.stdout.txt`                      |
| Gate 6 AI-use log          | DEFERRED，最终提交前补充真实 AI-use 记录                     | `ai-use-log-explicit.stdout.txt`                |

## 5. 关键安全验证

- 合规拒绝路径有效。
- `ad_014` 的 `banned_check=banned` 路径已由定向测试验证。
- 正常请求恰好产生 1 条匹配审计记录。
- 审计包含模型版本、prompt 版本和阈值溯源。
- 审计流程为：
  `output_exists → banned_words → banned_check → category → scene`
- Mock 评估集违规数为 0。
- Mock p95 为 0.0034 秒，不代表真实模型 SLA。

## 8. 结论

- V1 确定性离线核心：PASS
- 安全降级与审计链路：PASS
- Mock / Offline 测试范围：PASS WITH LIMITATIONS
- 完整课程 V1 交付：CHANGES REQUIRED

本报告不能作为完整课程 V1 交付 `APPROVE` 的依据。