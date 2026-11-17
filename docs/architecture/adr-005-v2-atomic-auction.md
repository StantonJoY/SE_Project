# ADR-005：V2 确定性竞价与原子预算结算

状态：实现方案，用户已授权本轮本地工作；经 AI 监督代理技术审查，团队正式人工验收待完成。不得将此状态改写为已获得新增具名人类技术批准。

## 背景与选择

V1 只选择广告。V2 新增跨请求预算，必须将状态、扣费和审计一致性显式设计。采用 SQLite，将预算、请求/结算结果和权威决策审计分表、同事务提交。

比较：JSON 账本加 JSONL 的分别写入不能保证同时成功；外部数据库与真实支付超出当前需求；SQLite 为标准库可用的本地持久化方案。V1 JSONL 运行路径保留；V2 的 JSONL 如导出，只是派生产物，不作为第二个权威提交点。

## 决策与权限边界

LLM 只提供逐候选相关性和理由，不接收或控制报价、花费、预算。确定性代码计算 relevance*bid 和 pay-as-bid 价格；同分按 ID。最终合规拒绝优先于结算；数据库事务还能因余额或证据失败拒绝提交。

报价、价格与预算为整数分，显式排除 bool；相关性整数 0–100。预算要求 remaining>=price。remaining=0 为 exhausted；正余额但支付不起报价时本轮排除。没有自动选择次优的隐含分支。

同 request_id 同输入返回保存的完整响应，既不重调模型也不扣第二次费。输入冲突明确拒绝。事务内再次检查唯一 ID、余额、状态、实际价格，不能信任调用前旧快照。故障注入必须证明预算、请求结果和权威审计全部回滚。

本地模拟订单提交是计费事件，不声称用户真实曝光。提交成功但响应丢失可用同 ID 恢复；提交状态无法核实时返回 status_unknown。基础设施故障下不能声称一定零费用或一定有持久审计。

## 文档、规则与变更

在原始 PDF 指定目录增量维护有效需求和工件，不把 docs2 或完全冻结旧源码当作额外课程门槛。保留现有实现、回归和只读合规判据；`.opencode/rules.md` 不由 agent 修改。

新增受保护路径应由真实门禁检查，不能仅写下规则。以下表需由现有检查器读入；代理评审与正式人类批准仍须分开。

<!-- safety-critical-paths -->

| 路径 | Plan | Build | 人工要求 |
|---|---|---|---|
| `src/bidding/` | Read | Write within plan | 安全语义变化须 ADR 与人工批准 |
| `src/app/pipeline_v2.py` | Read | Write within plan | 安全语义变化须 ADR 与人工批准 |
| `src/selector/relevance.py` | Read | Write within plan | 约束变化须 ADR 与人工批准 |
| `data/bids-v2.json` | Read | Write within plan | 报价/预算规则变化须 ADR 与人工批准 |
| `config-v2.yaml` | Read | Write within plan | 规则变化须 ADR 与人工批准 |
| `eval/v2_cases.json` | Read | Write within plan | 判据变化须 ADR 与人工批准 |
| `eval/v2_runner.py` | Read | Write within plan | 验证变化须 ADR 与人工批准 |

## 验证与重开条件

既有 V2 需求 REQ-ADS-ARCH-005 至 012、FR-005 至 008、NFR-SAFETY-006/007、NFR-QA-003/004、SEC-002、GOV-003、NFR-PERF-002 逐项映射测试。

一旦出现超支、重复扣费、合规拒绝仍收费、审计与已提交预算不一致，停止新成交并重审此决策。若增加真实曝光、多赢家、热更新报价、充值或外部支付，先扩展事件语义与事务设计。
