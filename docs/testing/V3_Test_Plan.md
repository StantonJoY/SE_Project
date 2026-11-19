# V3 测试计划（真实语料接入与内容分级）

> 状态：EXECUTING
> Run ID：`v3-20261120-53d37fc-01`
> 测试日期：2026-11-20
> 被测分支：`test/v3-validation`
> 被测代码 Commit：`53d37fcf933013af46714a7b29c084e4e07a6696`
> 来源分支：`origin/v3`
> 环境：Conda `SEProjectV3`
> Python：3.11.18
> Editable Project：`E:\cityu\SE\project\SE_Project-v3-test`

## 1. 测试目标

本轮验证 V3 的以下新增边界：

- 5,000 条 Steam 真实语料只读加载、校验和投影；
- 场景标签映射与确定性 top-K；
- `content_warnings ∪ content_descriptors` 三档内容分级；
- `required_age` 年龄兜底；
- V1 `--corpus` 和 V2 竞价结算接入；
- 广告费 = 定价 5%、预算 = 20 次曝光；
- V3 固定评估集、全量回归、变异验证与治理门禁；
- video demo 与 evidence 可追溯到同一 commit。

## 2. 测试边界

本轮不覆盖：

- BM25、embedding、向量检索或 RAG；
- 真实曝光确认、CPM/CPC 或商业计价；
- 用 MockLLM 结果证明语义推荐质量；
- 未经人工签字的 ADR-006 / TA-0005 正式批准。

## 3. 基线

| 项目 | 值 |
|---|---|
| 被测代码 Commit | `53d37fcf933013af46714a7b29c084e4e07a6696` |
| Worktree | `E:\cityu\SE\project\SE_Project-v3-test` |
| Conda 环境 | `SEProjectV3` |
| Python | 3.11.18 |
| 测试收集数量 | 675 |
| 收集退出码 | 0 |
| 证据目录 | `evidence/v3/v3-20261120-53d37fc-01/` |

## 4. 测试分层

| 层级 | 检查内容 | 当前状态 |
|---|---|---|
| L0 | 环境、editable install、模块路径 | PASS |
| L1 | 测试收集与基线冻结 | PASS，675 |
| L2 | 语料 manifest、SHA-256、边界样本 | BLOCKED |
| L3 | CorpusRepository 与 Ad 投影 | PENDING |
| L4 | 确定性与 top-K | PENDING |
| L5 | 内容分级与年龄兜底 | PENDING |
| L6 | V1 `--corpus` 端到端 | PENDING |
| L7 | V2 定价、竞价、幂等与预算 | PENDING |
| L8 | V1/V2/V3 replay 与全量回归 | PENDING |
| L9 | 变异、静态检查、治理门禁 | PENDING |
| L10 | Video demo 与最终证据 | PENDING |

## 5. 关键通过标准

- 语料行数、manifest、SHA-256 和边界样本一致；
- 5,000 条语料可通过 `AD_SCHEMA` 和 `AdRepository`；
- 空匹配返回空候选，K>50 被拒绝；
- `family`、`campus`、`competitive` 的 5×3 矩阵符合预期；
- Among Us 必须由 warnings 一侧拦截；
- 不传 `policy/facts` 时 V1 合规行为不变；
- V2 不得透支、重复扣费或出现账审不一致；
- 20 次成交后预算耗尽，第 21 次拒绝；
- V3 eval 14/14，违规 0，p95 < 5 ms；
- 全量 pytest 0 failed / 0 error；
- mutation 33/33；
- ADR-006、TA-0005 和 Gate 1 状态单独记录。

## 6. 预期限制

- `ADR-006` 当前为 `Proposed`；
- `TA-0005` 未签，Gate 1 可能 FAIL；
- MockLLM 按字典序选择，不能用于判断语义质量；
- V2 语料模式 top_k=4，是 token 估算差异导致的既定取舍；
- handover 中的部分统计数字可能与 manifest 不一致，必须以实际产物和测试为准。

## 7. Video Demo 计划

建议录制 8–10 分钟：

1. 环境、分支和 commit；
2. 5,000 条语料、manifest 与边界样本；
3. V1 `--corpus` 正常路径和审计；
4. family/campus/competitive 内容分级反例；
5. V2 5% 出价、幂等和预算递减；
6. 20 次耗尽与第 21 次拒绝；
7. V3/V1/V2 replay、全量测试和 mutation；
8. ADR-006、TA-0005、Gate 1 和 Mock/Live 边界。

## 8. 当前结论

环境和测试收集已完成；原 manifest hash 不一致已通过元数据修复解决，修复 commit 为 `15cc289`。修复后 V3 核心专项 49 项全部通过。全量回归被 3 个未跟踪的 V3 测试文档阻断；下一步提交文档并用新 commit 重跑全量测试，再进入 V1/V2 端到端、replay、mutation 和 video demo。
