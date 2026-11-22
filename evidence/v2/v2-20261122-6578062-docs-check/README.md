# V2 文档收尾时的验证

本目录是 2026-11-22 新运行的验证，源提交为 `65780628b724fdb6499625d45d4b8d9da5589bd0`。它不补造历史构建会话、前置批准或旧测试日志。具体命令、环境、退出码见 [run-manifest.json](run-manifest.json)。未调用外部模型服务，未修改产品代码/测试。

| 输出 | 结果 |
|---|---|
| `schema.stdout.txt` / `fitness.stdout.txt` | 当前需求与架构检查通过 |
| `v2-offline.stdout.txt` | 8 个 V2 测试模块：303 通过、1 跳过；bidding 覆盖率 95.59% |
| `loopback-rerun.stdout.txt` | 初次因回环端口受限跳过的单项测试，在放开本地端口限制后重跑通过 |
| `demo.stdout.txt` | 7 场景演示通过，主账本 3 条审计，总花费 440 分 |
| `v2-replay.stdout.txt` | 18 条、4 正向、14 预期拒绝、违规 0 |

每条命令同时保留 `stderr.txt`，空文件表示无 stderr 输出。测试本身的正常拒绝不计为违规。此处不是完整项目回归、远端 CI 或真实模型质量结论；本地通过也不替代正式人工批准。

[remote-ci-state.json](remote-ci-state.json) 保存对既有 main CI 的公开查询结果；它是远端状态快照，不是本次本地命令输出。[checksums.sha256](checksums.sha256) 用于核对本目录文件字节。
