# V1 Mock / Offline 演示命令

所有脚本应从仓库根目录执行。脚本用于复现
`evidence/v1/v1-20261104-a31860f-02/07-demo/screenshots/`
中的截图证据。

| 脚本 | 对应截图 |
|---|---|
| `01-environment.ps1` | `01-environment.png` |
| `02-offline-tests.ps1` | `02-tests.png` |
| `03-normal-recommendation.ps1` | `03-normal-recommendation.png` |
| `04-audit-record.ps1` | `04-audit-record.png` |
| `05-invalid-scene.ps1` | `05-invalid-input.png` |
| `06-eval-summary.ps1` | `06-eval-summary.png` |
| `07-safety-refusals.ps1` | `07-safety-refusals.png` |
| `08-static-checks.ps1` | `08-static-checks.png` |
| `09-evidence-integrity.ps1` | `09-repo-and-evidence.png` |
| `10-limitations.ps1` | `10-limitations.png` |

规则：

- 不包含 API key、密码或 token。
- 不修改生产审计日志。
- 截图命令仅读取已生成的 Run 02 证据。
- 所有结论限定为 Mock / Offline 范围。