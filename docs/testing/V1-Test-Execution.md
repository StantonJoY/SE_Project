# V1 测试执行记录

>  状态：COMPLETED_WITH_LIMITATIONS
>  有效运行：`v1-20261104-a31860f-02`
>  Run `v1-20261104-a31860f-01`：INVALIDATED
>  原因：Run 01 的 editable install 曾指向 `SE_Project-main`

## 1. 测试基线

| 项目 | 值 |
|---|---|
| 仓库 | `git@github.com:StantonJoY/SE_Project.git` |
| 本地测试目录 | `E:\cityu\SE\project\SE_Project-test` |
| 分支 | `test/v1-candidate-a31860f` |
| Commit | `a31860fc3fb7c0710cf2d7ed157d3ebab2dafe77` |
| 运行 ID | `v1-20261104-a31860f-01` |
| 测试模式 | mock |
| Python | 3.11.17 |
| 环境 | Conda `SEProject` |

## 2. 测试范围声明

本次测试仅覆盖 V1 Mock / Offline 模式。

范围内：
- 确定性规则与合规管道
- MockLLM 驱动的推荐与降级路径
- 固定评估集 replay
- 离线测试、静态检查、审计记录

范围外：
- 真实 LLM 接入
- live 测试
- 真实模型语义质量
- 真实 API 延迟、鉴权、限流与网络故障
- 课程 genuine AI component 的完整证明

## 3. 执行记录

| 测试 ID | 日期 | 检查项 | 命令 | 结果 | 退出码 | 证据 |
|---|---|---|---|---|---|---|
| ENV-001 | 2026-11-04 | Python 环境确认 | `python --version` | PASS | 0 | `environment.txt` |
| GIT-001 | 2026-11-04 | Git 基线确认 | `git rev-parse HEAD` | PASS | 0 | `git-commit.txt` |
| COL-001 | 2026-11-04 | 测试收集 | `pytest --collect-only` | PASS，299 个测试 | 0 | `pytest-collect.*` |
| LINT-001 | 2026-11-04 | Ruff 首次检查 | `ruff check src test scripts eval` | FAIL，3 项 | 1 | 终端记录 |
| LINT-002 | 2026-11-04 | Ruff 重跑 | `ruff check src test scripts eval` | PASS | 0 | `ruff.stdout.txt` |
| TEST-001 | 2026-11-04 | Ruff 修复后的定向测试 | `pytest test_repo_completeness.py test_audit.py` | PASS，31 个测试 | 0 | `targeted-tests-rerun.stdout.txt,targeted-tests-rerun.stderr.txt` |
| TEST-002 | 2026-11-04 | 全量 offline 回归第一次 | `pytest test/offline` | FAIL，298 passed / 1 failed | 1 | `offline-tests.stdout.txt` |
| TEST-002R | 2026-11-04 | 全量 offline 回归重跑 | `pytest test/offline` | PASS，299 passed | 0 | `offline-tests-rerun.stdout.txt`、`offline-rerun.junit.xml` |
| TEST-003 | 2026-11-04 | Run 02 全量 offline 回归 | `pytest test/offline` | PASS | 0 | `offline-tests.stdout.txt`、`offline.junit.xml` |
| TYPE-001 | 2026-11-04 | mypy | `python -m mypy --no-incremental` | PASS | 0 | `mypy.stdout.txt` |
| DEP-001 | 2026-11-04 | 依赖声明检查 | `python scripts/check_dependencies.py` | PASS | 0 | `dependencies.stdout.txt` |
| SCHEMA-001 | 2026-11-04 | 需求注册表与 Schema 校验 | `python scripts/validate_requirements.py` | PASS | 0 | `schema.stdout.txt` |
| ARCH-001 | 2026-11-04 | 架构 fitness function | `python scripts/fitness_functions.py` | PASS | 0 | `fitness.stdout.txt` |
| SAFETY-001 | 2026-11-04 | 安全路径标准检查 | `check_safety_paths.py --base origin/main` | FAIL | 1 | 基线退化，误含上一提交历史 |
| SAFETY-002 | 2026-11-04 | 当前修改显式检查 | `check_safety_paths.py --paths ...` | PASS | 0 | `safety-paths-explicit.stdout.txt` |
| IMPL-001 | 2026-11-04 | 实现与需求一致性审计 | `python scripts/audit_implementation.py` | PASS，0 发现 / 48 通过 | 0 | `implementation-audit.stdout.txt` |
| IMPL-002 | 2026-11-05 | Run 02 实现与需求一致性审计 | `python scripts/audit_implementation.py` | PASS，0 发现 / 48 通过 | 0 | `implementation-audit-02.stdout.txt` |
| E2E-001 | 2026-11-04 | 正常推荐路径 | `python -m app --time-slot night --device mobile --tag student` | PASS，kind=ad / ad_001 / 1 条审计 | 0 | `normal-02.stdout.json`、`normal-02.audit.jsonl` |
| E2E-002 | 2026-11-04 | 非法场景路径（测试环境曾指向 SE_Project-main） | `python -m app --time-slot midnight --device mobile` | PASS，no_ad / scene_invalid / 1 条审计 | 0 | `invalid-01.stdout.json`、`invalid-01.audit.jsonl` |
| E2E-003 | 2026-11-04 | Run 02 正常推荐 | `python -m app ...` | PASS，ad / ad_001，当前请求 1 条审计 | 0 | `normal-03.*` |
| E2E-004 | 2026-11-04 | Run 02 非法场景 | `python -m app ...` | PASS，no_ad / scene_invalid，当前请求 1 条审计 | 0 | `invalid-02.*` |
| EVAL-001 | 2026-11-04 | 固定评估集 replay | `python eval/eval_runner.py` | PASS，MUST_PASS 11/11，MUST_FAIL 14/14，违规 0 \| 0 | 0 | `eval-replay.stdout.txt`、`eval-replay.json` |
| EVAL-002 | 2026-11-04 | Run 02 固定评估集 replay | `python eval/eval_runner.py` | PASS，11/11 + 14/14，违规 0 | 0 | `eval-replay.stdout.txt`、`eval-replay.json` |
| SAFE-001 | 2026-11-04 | ad_014 禁止状态合规拒绝 | `pytest test_app_pipeline.py::test_degrade_compliance_rejected` | PASS，3 个参数用例通过 | 0 | `ad014-compliance.stdout.txt` |
| CLI-001 | 2026-11-04 | 非法 JSON 场景 | `python -m app --scene {badjson}` | PASS，退出码 2 | 2 | `invalid-json.stderr.txt` |
| CLI-002 | 2026-11-04 | 缺少场景参数 | `python -m app` | PASS，退出码 2 | 2 | `missing-args.stderr.txt` |
| CFG-001 | 2026-11-04 | 非法配置 loud fail | `python -m app --config <invalid-config.yaml>` | PASS，退出码 2 | 2 | `invalid-config.stderr.txt` |
| DATA-001 | 2026-11-04 | 素材文件缺失启动失败 | `python -m app --config <missing-data-config.yaml>` | PASS，退出码 2 | 2 | `missing-data.stderr.txt` |
| MUT-001 | 2026-11-04 | 变异验证 | `python scripts/mutation_check.py` | INCONCLUSIVE，12 条有效，INV-ADS-016 为工具假阳性 | 0 | `mutation-check.stdout.txt` |
| GOV-001 | 2026-11-04 | 语义评估门禁 | `check_semantic_eval.py --base origin/main` | PASS，不适用 | 0 | `semantic-eval.stdout.txt` |
| AUD-001 | 2026-11-04 | 正常请求审计字段与版本溯源 | 手工解析 `normal-03.audit.jsonl` | PASS，字段完整且当前请求恰好 1 条 | 0 | `normal-03.audit.jsonl` |
| GATE1-001 | 2026-11-05 | Gate 1 当前工作区检查 | `check_test_approval.py --files ...` | PASS，当前变更不含测试文件 | 0 | `test-approval-explicit.stdout.txt` |



## 4. 缺陷记录

### DEF-001：Ruff 静态检查失败

- 发现时间：2026-11-04
- 严重级别：S2
- 状态：FIXED，等待全量回归验证
- 症状：Ruff 报告 3 个问题
- 根因：代码可使用更简洁写法，且存在未使用循环变量与可移除的注解引号
- 修改文件：
  - `scripts/check_repo_completeness.py`
  - `src/audit/store.py`
- 修复：
  - 使用 `any()` 简化构建目录判断
  - 删除未使用的循环变量
  - 删除 `AuditStore` 注解中多余的引号
- 验证：
  - Ruff 已通过
  - 相关 31 个测试已通过
- 待办：全量回归通过后才能改为 `VERIFIED`

### DEF-002：README 测试数量与实际情况不一致

- 发现时间：2026-11-04
- 严重级别：S2
- 状态：OPEN
- README 记录：285 个测试
- 实际收集：299 个测试
- 暂不修改，等待测试执行完成后统一同步文档

### DEF-003：安全路径检查器的基线退化

- 严重级别：S2
- 状态：OPEN
- 触发条件：当前分支 HEAD 与 `origin/main` 指向同一个 commit
- 症状：分支差异为空后，检查器把未提交变更和 `HEAD~1..HEAD` 合并
- 本次误报：`scripts/fitness_functions.py`
- 影响：无法区分当前工作区修改和上一个已合并提交
- 暂不修复，等待治理评审

### DEF-004：审计模块未纳入受保护路径

- 严重级别：S1
- 状态：OPEN
- 涉及路径：`src/audit/`
- 现状：`src/audit/store.py` 修改后，安全检查器返回“未触及受保护路径”
- 风险：审计证据子系统可被修改而不触发 ADR 检查
- 暂不修改 ADR，等待架构负责人确认

### DEF-005：实现审计的素材拒绝覆盖未统计 banned_check

- 严重级别：S2
- 状态：OPEN
- 症状：`ad_014` 标记为 `banned_check=banned`，但 [G] 输出为“从未被任何 gate 拒绝”
- 已知业务测试：`test_app_pipeline.py::test_degrade_compliance_rejected[ad_014-banned_check]`
- 初步判断：实现审计脚本的覆盖视图不完整，V1 运行路径仍可能正确
- 处置：暂不修复，后续由全量测试和定向复测确认


- 状态：OPEN，仅审计工具覆盖缺口
- 业务路径验证：已由 `test_app_pipeline.py::test_degrade_compliance_rejected` 验证
- 运行路径结论：正确

### DEF-006：测试文档未进入 Git 索引导致完整性检查失败

- 严重级别：S3
- 状态：待验证
- 原因：新建的 `docs/testing/V1-Test-Execution.md` 尚未被 Git 跟踪
- 处置：暂存测试文档后重跑全量测试


- 状态：FIXED / VERIFIED
- 修复：暂存 `docs/testing/V1-Test-Execution.md`
- 验证：全量回归 299 passed

### DEF-008：变异验证将 pytest INTERNALERROR 误判为检出

- 严重级别：S2
- 状态：OPEN
- 涉及变异：`INV-ADS-016 / MUT-GATE-ALWAYS-PASS`
- 症状：子进程报 `ModuleNotFoundError: No module named 'eval_runner'`
- 判定问题：`_classify()` 未排除 INTERNALERROR
- 影响：无法证明 INV-ADS-016 的测试具备证伪能力
- 暂不修复

### DEF-009：Gate 1 测试批准门禁失败

- 严重级别：S1
- 状态：OPEN
- 原因：`test/offline/test_repo_completeness.py` 无实现前批准记录
- 性质：历史治理缺口，不应通过补写过去时间戳来伪造
- 处置：保留缺口记录，后续新测试必须严格先批准后实现

### DEF-010：Gate 6 AI-use log 延期

- 严重级别：S1
- 状态：DEFERRED
- 原因：Mock / Offline 测试阶段暂不更新 AI-use log
- 处置：最终课程提交前，根据实际 Opencode 和人工参与情况追加真实 AIU entry
- 当前不视为 PASS

### 延期项：Gate 6 AI-use log

当前 Mock / Offline 测试阶段暂不更新 AI-use log。
原因：该记录应在最终提交前，根据实际 agent 使用、人工操作和审核情况统一填写。
当前状态：DEFERRED，不计为 PASS。
后续动作：提交前追加真实 AIU entry，并重新运行 check_ai_use_log.py。


## 6. 测试结论

Mock / Offline Scope: PASS WITH LIMITATIONS
Course Submission Readiness: CHANGES REQUIRED