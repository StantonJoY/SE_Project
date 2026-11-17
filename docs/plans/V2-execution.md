# V2 执行计划与真实授权边界

基线：a31860fc3fb7c0710cf2d7ed157d3ebab2dafe77。目标：在 V1 上增加单赢家竞价和持久预算结算。

## 1. 来源与授权

课程依据为用户最初提供的 CS5351 项目说明 PDF。该说明优先于仓库附加的 docs2、整包冻结和互盲实现习惯。保留原 V1 行为与测试，保持 `.opencode/rules.md` human-only 不修改。

用户于 2026-10-30T12:10:56.447Z 授权本地执行此前审阅的 V2 修订方案，并委托监督代理与各 agent 交互，记录中断、重定向、批准、拒绝及理由。原始授权消息保存在本地会话归档。

技术计划、测试设计和修改意见由 AI 监督代理评审。团队正式验收、人工前置批准和真实模型验证的状态分别记录在 [V2 审批状态](../v2-approval-status.yaml)。

## 2. 需求与架构

覆盖注册表中既有 19 条 V2 候选语义 ID：NFR-SAFETY-006/007、ARCH-005 至 012、FR-005 至 008、NFR-QA-003/004、SEC-002、GOV-003、NFR-PERF-002，均带 REQ-ADS 前缀。

选择 SQLite 同库分表，预算、请求结果与权威审计同事务提交。拒绝 JSON 账本与独立 JSONL 双写方案，因为它们不能自然保证扣费和审计一致。详见 ADR-005。

单赢家；pay-as-bid；金额整数分；相关性 0–100 整数；score=relevance*bid；平局按 ID 升序。合规在结算前，低余额不成交；同一逻辑请求只提交一次。无真实支付、曝光确认、RAG 或 top-N。

## 3. 接口与范围

- `bidding`: Bid、validate_bids、AuctionChoice、choose_winner、Ledger、BidError、LedgerError、RequestConflict、InsufficientBudget。
- `Ledger`: seed、budgets、lookup、finalize、audit_records（仅离线验证）、close。finalize 同事务重查唯一请求和余额，更新预算，保存响应和一条完整证据。
- `selector.relevance`: score(scene,candidates)->原始 JSON；严格 parse_relevance_output；固定分数和真实可配置 HTTP 提供者。
- `app.pipeline_v2.recommend_v2`: 接收场景、request_id 和显式依赖，返回 ad/no_ad/status_unknown。
- V2 CLI、V2 渲染 schema、独立报价 sidecar、演示与固定评估；V1 API 与安全判据保持。

文件范围：新增 src/bidding、selector/relevance.py、app/pipeline_v2.py/cli_v2.py、render/schema_v2.py、data/bids-v2.json、config-v2.yaml；新增 V2 测试和评估。需求、架构和必要检查器在原指定目录增量更新，不创建 docs2 平台。

允许标准库 sqlite3/json/urllib/threading 等和已声明依赖。不修改人类专属规则文件，不削弱原合规条件，不删测/跳测，不提交密钥，不推送或发布。

## 4. 测试设计（实现前已给定的策略）

规格驱动反例：错误报价类型/范围、重复或未知 ID、评分缺失/重复/集外/额外字段/bool/NaN/Inf、固定评分与平局、候选重排、预算恰好够/不足/耗尽、暂停、合规拒绝零扣费、同 ID 重试和冲突、两个连接争抢预算、事务 after_debit/before_audit/before_commit 故障、重启恢复、响应丢失重试、固定快照重放。

V1 全套回归；至少 10 条 V2 固定评估；保留团队既有覆盖率和计算性能指标。所有安全反例必须符合预期，不能只打印不阻断。live 与离线验证分开，不用 Mock 证明真实模型质量。

## 5. 实际分工与检查点

1. CLI PLAN 尝试：只读，连接重试后被监督代理终止；保留原 stdout/stderr/精确 prompt。
2. Native PLAN：输出候选比较、接口和测试设计，无代码修改。
3. 监督代理评审：修正扣费顺序、事务审计、余额判定、幂等及状态未知语义；属于 proxy_review。
4. 独立 TEST：依据接口写测试，不读新实现。BUILD 分为核心和集成两位实际 agent，不修改测试断言。
5. VERIFY：结构、回归、行为评估，发现问题交回对应 BUILD；所有修复与重定向原样保留。
6. 交接：仓库提供源代码、演示、测试和评审摘要。原始会话、工具输出及干预注释在本地归档，由团队在课程要求时另行提交。正式人工验收单独记录。

## 6. 回退与未知结果

本轮仅在本地功能分支，不合并远程 main。不成功的预算事务回滚；已提交但响应未知的请求用同一 request_id 查询恢复。不得将状态未知伪报为未收费。数据库全不可用时无法保证持久化审计，这一异常应明确报告，不承诺不可能实现的保证。
