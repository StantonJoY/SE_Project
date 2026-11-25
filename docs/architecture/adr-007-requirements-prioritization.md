# ADR-007：需求优先级（MoSCoW）与显式取舍记录

> **状态**：**`Accepted`**（2026-11-25 由人类所有者批准）
> **日期**：2026-11-25 · **决策者**：A（产品/流程）+ B（架构）· **批准人**：Shen Jiyun（60989886）
> **触及的受保护路径**：`docs/req/requirements.yaml`、`docs/req/req-schema.json`
> **关联**：课程 D1 原文「Prioritization uses MoSCoW, and states the tradeoff explicitly」；
> `INV-ADS-010`（需求变更须 ADR）；`TD-018`（门禁 1 历史缺口，见取舍 #4）

---

## 1. 背景

课程 D1 要求两件事：

1. 需求用 **MoSCoW** 排序；
2. **显式说明取舍**（states the tradeoff explicitly）。

仓库此前只满足第 1 条：`requirements.yaml` 的每条需求有 `priority: must|should`（58 条 must、3 条 should），
但**没有任何一处写明"为了做到 must，我们放弃了什么"**。

`scope.out` 记的是"不做什么功能"，不是"取舍"——它没有说清代价与受影响的需求。
评审按课程条目找"tradeoff"，找不到就会判 D1 不完整。

## 2. 决策

在 `docs/req/requirements.yaml` 增加顶层 `prioritization` 段（同时扩展 `req-schema.json`）：

```yaml
prioritization:
  method: "MoSCoW"
  distribution: {must: 58, should: 3}
  tradeoff_policy: <must/should 的定义 + 降级规则>
  tradeoffs:
    - decision / gave_up / why / refs
```

四条取舍（`refs` 指向受影响的需求）：

| # | 取舍 | 放弃了什么 |
|---|---|---|
| 1 | V3 用确定性标签匹配，不做 RAG | 长尾语义匹配 |
| 2 | 广告费 = 定价 5%，不做对账 | 真实计费正确性 |
| 3 | V2 语料候选上限压到 4 条 | 竞价候选多样性 |
| 4 | 门禁 1 对 V3 历史保持红，不回填 | 一条全绿的门禁记录 |

## 3. 为什么放在注册表而不是报告里

课程把这条要求写在 **D1（需求交付物）** 下。放进报告会让"需求文档"与"优先级依据"分离，
评审要跨文件拼；放进注册表则与 `priority` 字段同源，且能被 Schema 校验
（`tradeoffs` 不得为空、`refs` 必须是真实需求 ID）。

## 4. 被否的备选

| 备选 | 为什么不选 |
|---|---|
| 只写进 `Report.md` | 与 `priority` 字段不同源，容易漂移；且 D1 要求的是需求文档 |
| 复用 `scope.out` 的 `rationale` | 语义不同：`out` 是"不做的功能"，tradeoff 是"做了 A 所以失去 B" |
| 每条需求各写一个 `tradeoff` 字段 | 61 条里多数没有真实取舍，会产出大量套话；且改动面过大 |

## 5. 后果

- 好处：D1 的"显式取舍"可被评审直接读到；四条取舍都挂在真实需求 ID 上，可追溯。
- 代价：注册表多一个顶层段，Schema 收紧（`tradeoffs` 至少 1 条、`refs` 至少 1 个 ID）。
- **诚实边界**：`distribution` 的数字来自 `priority` 字段的实测分布（58/3），
  Schema 只校验类型，不校验与条目的一致性——这属于 `TD-027`（文档与实现一致性无法机械检验的子集）。

## 6. 重开条件

1. 出现 `could` / `won't` 级别的需求（当前为 0）；
2. 任一条 must 降级为 should；
3. 取舍条目与实际实现不符（例：真的接入了对账）。

---

## 人工批准记录

| 项 | 内容 |
|---|---|
| 批准人（具名人类） | Shen Jiyun（60989886，仓库所有者） |
| 批准时间 | 2026-11-25 |
| 结论 | `Accepted` |
| 备注 | 本记录由 agent 依人类指示录入，不是 agent 自我批准；依据为人类在会话中对该决策的确认 |

> **No agent may self-approve**（课程 §11.3）。
