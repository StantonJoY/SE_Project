# 汇报准备计划（20 分钟 · A / D 分工）

> **来源**：课程 PDF 没有 presentation 章节，只规定 D1–D7 交付物；汇报依据老师公告的 7 个方面。
> **已定**：时长 **20 分钟**；讲者 **A（Shen Jiyun）+ D（Gao Zhechun）**，D 从**第 12 页**接手。
> **交付物**：`CS5351_Group26_Presentation.pptx`（20 页，CityU 模板）+ `PRESENTATION-SCRIPT.md`（逐页讲稿）。
> **主线**：讲清 V1→V2→V3 **每一轮为什么改、怎么设计、放弃了什么**，而不是只展示最终形态。
> 更新：2026-11-27

---

## 1. 老师公告（原文）

> Your group may select one or more members to deliver the presentation in person.
>
> The presentation should explain your team's software engineering process from start to finish.
> Please cover the following areas:
>
> 1. **Requirements and specification**: How did you turn initial ideas into clear functional and
>    non-functional requirements? How did you refine them and define how to verify that they were met?
> 2. **Architectural design and integration**: What were the main design decisions for the new
>    features? How did you guide their implementation and integrate them into the existing codebase
>    while keeping complexity manageable?
> 3. **Team coordination and individual contributions**: Explain how your team divided and
>    coordinated the work, and summarize each member's actual contributions, such as requirements,
>    design, agent supervision, implementation, testing, code review, or project management.
> 4. **Human–agent interaction**: What were the agents' actual responsibilities, when and how were
>    they invoked, and how did team members review, approve, correct, or redirect their output?
> 5. **Traceability throughout development**: How did you maintain the links between requirements,
>    design, code, and tests as new requirements, implementation changes, and bug fixes were
>    introduced over the weeks?
> 6. **Code review, quality assurance, and CI/CD**: What review strategies and tests did you use to
>    assess the generated code? What CI/CD gate checks were implemented, and how did they prevent
>    unsuitable changes from being merged or released?
> 7. **Challenges, rework, and improvement**: What significant problems did you encounter, how did
>    you resolve them, and what needed to be revised? Explain what your team learned and how you
>    improved the development process.

---

## 2. 逐条覆盖核对

| # | 公告要求 | 覆盖 | 幻灯片 | 证据（可现场打开） |
|---|---|---|---|---|
| 1 | Requirements and specification | ✅ | 3–6 | 三轮对照表；`requirements.yaml`（类型化 + 四条取舍） |
| 2 | Architectural design and integration | ✅ | 7–8 | 权威链；`git diff` 证明 `ads/`、`scene/` 未动 |
| 3 | Team coordination and individual contributions | ✅ | 9 | `Report.md` §3（角色 + 1.333 / 0.889×3） |
| 4 | Human–agent interaction | ✅ | 10–11 | `test-approvals.yaml`（TA-0005 时序）、`review-memo.md` |
| 5 | Traceability throughout development | ✅ | 12–13 | 覆盖表 + `test_v3_pricing.py` + 变异 `assert 50 != 75` |
| 6 | Code review, QA, CI/CD | ✅ | 14–16 | 七道门禁；`evidence/v3/v3-20261125-github-gates/{1,2,3}.png` |
| 7 | Challenges, rework, improvement | ✅ | 17–18 | `Report.md` §7.9；`debt-register.md` |
| — | 允许 1 人或多人现场讲 | ✅ | — | 已定 **A + D**；D 从第 12 页接手 |

**覆盖结论**：7 个方面全部有对应幻灯片与仓库证据；无遗漏项。

---

## 3. 分工与时间（**D 从第 12 页开始**）

| 页 | 幻灯片标题 | 讲者 | 累计时间 |
|---|---|---|---|
| 1 | 封面（主张 + 三轮主线） | **A** | 0:00 |
| 2 | 三个数字 61 / 679 / 33（22+19+20，无删除） | A | 0:30 |
| 3 | **三轮，三个不同的问题**（对照表：动因 / 变化 / 放弃） | A | 1:15 |
| 4 | 第二轮：竞价把什么写进了需求 | A | 3:00 |
| 5 | 第三轮：真实数据改的是需求 | A | 4:20 |
| 6 | 每轮都必须可校验，并且说出代价 | A | 5:45 |
| 7 | 一条权威链 | A | 6:45 |
| 8 | 三轮，一套代码：只扩展不替换 | A | 7:45 |
| 9 | 四个角色与贡献 | A | 8:30 |
| 10 | 三种角色：写实现的不能读测试 | A | 9:10 |
| 11 | agent 犯的错 | A | 9:55 |
| **12** | **可追溯：一条链（D 接手）** | **D** | 10:40 |
| 13 | FR-012：从一句话到一次变异 | D | 11:30 |
| 14 | 七道门禁 | D | 12:20 |
| 15 | 门禁真的会拦（直推被拒 + 6/7） | D | 13:15 |
| 16 | 规则页与 PR 列表 | D | 14:10 |
| 17 | 三个转折 | D | 14:50 |
| 18 | 还不成立的四处 | D | 15:45 |
| 19 | 现场演示（D 讲解 + D 操作） | **D** | 16:35 |
| 20 | 收尾 | **D** | 18:35 |

**交接点**：A 在第 11 页末尾说 *"D will take you through traceability, the gates, and what we changed."*
**此后到结束全部由 D 承担**：第 12–18 页讲解、第 19 页演示（自己讲解 + 操作）、第 20 页收尾。
**缓冲**：19:10–20:00 留给 Q&A。

---

## 4. 逐页要点（只讲节点与框架）

| 页 | 一句话要点 | 现场可打开的证据 |
|---|---|---|
| 1 | 三轮迭代，每轮由上一轮做不到的事触发 | `README.md` |
| 2 | 61 是 22+19+20 累加，不是替换 | `requirements.yaml` |
| 3 | 三个"为什么"：约束 AI / 引入竞争 / 真实数据；第 4 列是"放弃什么" | 表格本身 |
| 4 | 竞价 → 整数分、单事务、pay-as-bid、合规在竞价之后 | `src/bidding/ledger.py` |
| 5 | schema 不变（旁路 facts）、分级在场景步内、`policy=None` 等于 V1 | `src/compliance/` |
| 6 | 类型决定必填字段；四条取舍登记在册 | `prioritization` 段 |
| 7 | 合规在模型之后且可否决；`selector/` 不得 import `compliance/` | blueprint 权威图 |
| 8 | V2/V3 均为增量；`git diff` 可验证 | `git diff` |
| 9 | 角色先定，1.333 / 0.889×3，平均 1.000 | `Report.md` §3.2 |
| 10 | 写实现的不读测试；让测试变绿只能改实现 | `test-approvals.yaml` |
| 11 | 假反例 / 0-job CI / CRLF 哈希 | `bug-diary.md` |
| 12 | 八个脚本各守一环 | 覆盖表 |
| 13 | $14.99→75 分；5%→10% 时 `assert 50 != 75` | `test_v3_pricing.py` |
| 14 | 七道门禁；Gate 1 比时间戳 | `ci.yml` |
| 15 | 直推被拒原文；6/7 的真实 PR | 三张截图 |
| 16 | 六道必需检查 + bypass 披露；`docs/` 免审但必须过 CI | 规则页截图 |
| 17 | 三个转折：触发→改动→代价 | `Report.md` §7.9 |
| 18 | 四处不成立（承接第 6 页） | `debt-register.md` |
| 19 | 两档位结果不同；幂等不二次扣费（D 操作） | 终端 |
| 20 | 不是推荐器，是"让诚实可被检查"的装置（D 收尾） | — |

---

## 5. 现场演示（2 分钟）

```bash
# 1) 同一场景、两个档位 → 结果不同
python -m app --corpus --time-slot afternoon --device desktop --tag family
python -m app --corpus --time-slot afternoon --device desktop --tag student

# 2) 5% 定价 + 竞价 + 幂等（同 request-id 第二次不扣费）
python -m app.cli_v2 --corpus --request-id demo1 --time-slot afternoon --device desktop --tag family --db demo.sqlite3
```

**兜底**：`docs/testing/V3-Demo-Screenshots.md` 的 10 张图（离线可放）。

---

## 6. Q&A 预演（全员在场）

| 问题 | 30 秒答案 |
|---|---|
| 为什么第二轮不做次价？ | 理论更优但难解释、易被策略化；pay-as-bid 可解释、可审计、无策略空间 |
| V3 为什么不改 Ad schema？ | 会触碰 V1/V2 契约与全部既有测试；旁路 facts 让 V1 代码零改动 |
| 分级为什么不做第六步？ | 第五步已握有场景与品类；加第六步要重写"五步"契约与 36 条不变量 |
| Gate 1 为什么红？ | V3 测试写于 11-17；保留缺口（TD-018），TA-0005 建前向机制 |
| 为什么不用 RAG？ | 向量库破坏零依赖与可复现；13 条被否方案在 `option-ledger.md` |
| 怎么证明测试有效？ | 变异 33/33；第一次跑抓出 4 条"怎么改都绿"的假反例 |
| 5% 有依据吗？ | 演示口径、无对账；真实计费引入税/退款/币种三条失败路径 |
| 贡献怎么算的？ | 角色先定 + 交付物对照 + 团队会议确认；平均 1.0 |
| 如果多两周？ | 统一两套 token 估算；接真实计费；monitor 全覆盖；Gate 1 全绿 |

---

## 7. 准备清单

- [x] 时长 20 分钟、讲者 A + D（D 从第 12 页接手）
- [x] 幻灯片 20 页（CityU 模板，演讲者备注含讲稿）
- [x] 逐页讲稿 `PRESENTATION-SCRIPT.md`
- [ ] 在**目标机器**上预跑演示命令（依赖 2.1 MB 语料，已入库）
- [ ] 离线备份：截图 + 录屏（防现场环境故障）
- [ ] 每人准备 1 个"我做的具体决定"故事（30 秒）
