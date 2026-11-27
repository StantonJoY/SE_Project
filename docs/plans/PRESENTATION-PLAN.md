# 汇报（Presentation）准备计划

> **来源**：项目要求 PDF **没有** presentation 章节——它只规定 D1–D7 交付物与提交格式
> （`Week1_Project_Requirements.pdf`：1 Overview / 2 Team / 3 Deliverables / 4 Submission /
> 5 Repo Structure / 6 Blocking Gates）。
> 因此**汇报的唯一依据是老师公告**（2026-11-27），本文件按公告的 7 个方面组织。
> 建立：2026-11-27

---

## 1. 公告的硬性要求（逐条）

| # | 公告原文要点 | 我们的对应章节 |
|---|---|---|
| 1 | Requirements and specification：想法 → 功能/非功能需求；如何细化、如何定义"怎么验证" | `Report.md` §1 |
| 2 | Architectural design and integration：主要设计决策；如何指导实现并接入既有代码；如何控制复杂度 | §2 |
| 3 | Team coordination and individual contributions：怎么分工协调；每人实际贡献 | §3 |
| 4 | Human–agent interaction：agent 实际职责、何时/如何调用、人如何审查/批准/纠正/重定向 | §4 |
| 5 | Traceability：需求 ↔ 设计 ↔ 代码 ↔ 测试 如何随周演进保持链接 | §5 |
| 6 | Code review, QA, CI/CD：评审策略与测试；门禁检查；如何阻止不合格变更被合并 | §6 |
| 7 | Challenges, rework, improvement：重大问题的解决与修订；学到什么；流程如何改进 | §7 |

**约束**：可以一人讲，也可以多人讲（"one or more members"）。**没有规定时长**——
需向助教确认；下面按 **15 分钟**（12 分钟讲 + 3 分钟演示/问答）设计，另给 8 分钟精简版。

---

## 2. 15 分钟时间分配

| 时间 | 内容 | 讲者建议 |
|---|---|---|
| 0:00–1:00 | 开场：一句话主张 + 三个数字 | A（PM） |
| 1:00–3:00 | ① 需求与规格：61 条、类型化、fit criterion、MoSCoW + 四条取舍 | A |
| 3:00–5:30 | ② 架构与集成：9 元素、权威链、V2/V3 如何"扩展而不改基线" | A |
| 5:30–7:00 | ③ 团队分工与贡献：角色表 + 33.33%/22.22%×3 + 每人的代表性交付 | B（或各人各 20 秒） |
| 7:00–8:30 | ④ 人–agent 协作：盲测协议、TA 批准、agent 犯的错 | B |
| 8:30–10:00 | ⑤ 可追溯性：一条需求走通全链路（FR-012 → 5% → 变异） | C |
| 10:00–11:30 | ⑥ 评审/QA/CI：7 道门禁 + 那张"6 绿 1 红"的图 | D |
| 11:30–12:00 | ⑦ 挑战与改进：三张表（假反例、0-job CI、CRLF 哈希） | D |
| 12:00–15:00 | 现场演示 3 条命令 + 门禁证据图 + Q&A | 全体 |

**8 分钟精简版**：①1.5′ ②2′ ③1′ ④1.5′ ⑤1′ ⑥1.5′ ⑦0.5′（演示压缩成一张图）。

---

## 3. 逐页提纲（建议 14–16 页）

| 页 | 标题 | 讲什么（要点） | 证据（可现场打开） |
|---|---|---|---|
| 1 | 标题 + 团队 | 项目名、四人姓名学号、仓库地址 | `README.md` |
| 2 | 一句话主张 | **AI 是顾问，代码是执行官**；61 需求 / 679 测试 / 33 变异 | `Report.md` 摘要 |
| 3 | ① 需求怎么来 | 从 proposal → 22/19/20 三轮；类型化（不变量 26 条）；每条必须写"怎么验证" | `docs/req/requirements.yaml` 头 30 行 |
| 4 | ① 取舍是显式的 | MoSCoW 58 must / 3 should + 四条真实取舍（RAG 换标签匹配、5% 不对账、V2 只装 4 条、门禁 1 不回填） | `requirements.yaml` 的 `prioritization` 段 |
| 5 | ② 架构：权威链 | 请求 → sanitize → 候选 → LLM 建议 → （V2 竞价）→ **合规五步** → 渲染 → 审计 | `architecture-blueprint.md` 权威图 |
| 6 | ② 扩展而不改基线 | V2 新增 `bidding/`、V3 新增 `corpus/`；`ads/`、`scene/` 零改动；`policy=None` 与 V1 逐位一致 | `git diff --stat origin/main~20..main -- src/ads src/scene` |
| 7 | ③ 分工 | 4 个角色 → 33.33 / 22.22 ×3；每人一句"代表作" | `Report.md` §3.2 |
| 8 | ④ 人–agent | BUILD/VERIFY/TESTER 三角色；**盲测**；TA-0005 的 92 秒时序 | `docs/test-approvals.yaml` |
| 9 | ④ agent 犯的错 | 4 条"不能失败的假反例"；CI 7 次 0 job；CRLF 导致的哈希不一致 | `docs/review-memo.md` 的 BUG 表 |
| 10 | ⑤ 一条需求走通 | FR-012 → `pricing.py` → 3 条测试 → `MUT-V3-BID-TEN-PERCENT` 红 | `test_v3_pricing.py` + 变异输出 |
| 11 | ⑥ 七道门禁 | Gate 1–6 + 5b 各管什么；一图：6 绿 1 红 | `docs/testing/V3-GitHub-Gate-Evidence.md` 的 3 张图 |
| 12 | ⑥ 门禁真的会拦 | 直推被拒的报错原文；分支保护对 docs 与 src 的区别 | `docs/branch-protection.md` §9 |
| 13 | ⑦ 三个转折 | 假反例 → 加变异门；0-job → "先看 job 数"；三处漂移 → 单一来源 + 审查 | `Report.md` §7.9 |
| 14 | ⑦ 还没解决的 | Gate 1 历史红（TD-018）、monitor 只接 2/22（TD-001）、语料 5000/25899、5% 是演示口径 | `docs/debt-register.md` |
| 15 | 现场演示 | 见 §4 | 终端 |
| 16 | 结尾 | "让诚实可检查" + 我们的三条自我限制 | — |

---

## 4. 现场演示（3 分钟，离线可跑）

```bash
# 1) V1：真实语料 + 内容分级（同一个场景换档位，结果不同）
python -m app --corpus --time-slot afternoon --device desktop --tag family     # 出 ad
python -m app --corpus --time-slot afternoon --device desktop --tag student    # 多数被拒

# 2) V2：5% 定价 + 竞价 + 预算扣减（同一账本连跑两次）
python -m app.cli_v2 --corpus --request-id demo1 --time-slot afternoon --device desktop --tag family --db demo.sqlite3
python -m app.cli_v2 --corpus --request-id demo1 ... # 幂等：同结果、不二次扣费

# 3) 门禁：一条命令看 33 条变异
python scripts/mutation_check.py --list | head
```

**备用**：若现场网络/环境有问题，直接用 `docs/testing/V3-Demo-Screenshots.md` 的 10 张图。

---

## 5. 高概率 Q&A（附 30 秒答案方向）

| 问题 | 答案要点 |
|---|---|
| 你们怎么证明测试有效？ | 变异验证 33/33；第一次跑抓出 4 条"怎么改都绿"的假反例 |
| Gate 1 为什么是红的？ | V3 测试写于 11-17，具名批准只能之后作出；我们选择登记缺口（TD-018）而不是改日期；TA-0005 建立了前向机制 |
| 为什么不用 RAG？ | 需引入向量库，破坏零依赖与可复现；已写进 `option-ledger.md` 的 13 条被否方案 |
| AI 会不会绕过合规？ | 结构上不可能：`selector/` 不能 import `compliance/`；合规是 FINAL AUTHORITY；有 5 条不变量 + 变异锁定 |
| 5% 定价有依据吗？ | 演示口径，无对账；真实计费会引入税/退款/跨币种三条失败路径，已写进取舍 |
| 子集只有 5000 条？ | 分层抽样，边界样本全含；manifest 带 SHA-256，可重算 |
| 你们的分工可信吗？ | 角色先定、交付物对照、2026-11-25 团队会议确认；贡献表平均 1.0 |
| 如果给你更多时间？ | ①统一两套 token 估算口径 ②接真实曝光计费 ③monitor 全覆盖（TD-001）④Gate 1 全绿 |
| agent 写过的最差代码？ | CI 0-job 那次的 workflow env；CRLF 哈希；prompt 里给模型塞了内部文档路径 |
| 为什么 30% 时间在治理？ | 因为"绿徽章会撒谎"——0-job 事件证明了这一点 |

---

## 6. 讲者安排（两种方案）

| 方案 | 适合 | 分工 |
|---|---|---|
| **单人主答** | 一人时间充裕 | A 讲 1–4、7；A 或 D 讲演示；其余成员在 Q&A 补充 |
| **两人分工**（推荐） | 展示团队 | A：① ② ③ + 开场结尾；D：④ ⑤ ⑥ ⑦ + 演示（最熟证据链） |

> 公告允许 "one or more members"，但**Q&A 时全员在场**更稳，尤其"某块是谁做的"这类问题。

---

## 7. 准备清单

- [ ] 确认**时长**（问助教：10 / 15 / 20 分钟）
- [ ] 确认**讲者**（1 人还是 2 人）
- [ ] 现场演示在**目标机器**上预跑一遍（`python -m app --corpus` 需要 2.1 MB 语料，已入库）
- [ ] 三张门禁图（`evidence/v3/v3-20261125-github-gates/{1,2,3}.png`）放进 PPT
- [ ] 离线备份：截图 + 录屏（防现场环境故障）
- [ ] 每人准备 1 个"我做的具体决定"故事（30 秒）
