# 汇报准备计划（20 分钟 · A / D 分工）

> **来源**：课程 PDF 没有 presentation 章节，只规定 D1–D7 交付物；汇报依据老师公告的 7 个方面。
> **已定**：时长 **20 分钟**；讲者 **A（Shen Jiyun）+ D（Gao Zhechun）**。
> **交付物**：`CS5351_Group26_Presentation.pptx`（18 页，CityU 模板）+ `PRESENTATION-SCRIPT.md`（逐页讲稿）。
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

| # | 公告要求 | 是否覆盖 | 幻灯片 | 证据（可现场打开） |
|---|---|---|---|---|
| 1 | Requirements and specification | ✅ | 3–4 | `docs/req/requirements.yaml`（类型化 + `prioritization` 四条取舍） |
| 2 | Architectural design and integration | ✅ | 5–6 | `architecture-blueprint.md` 权威链；`git diff` 证明 `ads/`、`scene/` 未动 |
| 3 | Team coordination and individual contributions | ✅ | 7 | `Report.md` §3（角色 + 1.333 / 0.889×3） |
| 4 | Human–agent interaction | ✅ | 8–9 | `docs/test-approvals.yaml`（TA-0005 时序）、`docs/review-memo.md`（BUG 表） |
| 5 | Traceability throughout development | ✅ | 10–11 | 覆盖表 + `test_v3_pricing.py` + 变异 `assert 50 != 75` |
| 6 | Code review, QA, CI/CD | ✅ | 12–14 | 七道门禁；`evidence/v3/v3-20261125-github-gates/{1,2,3}.png` |
| 7 | Challenges, rework, improvement | ✅ | 15–16 | `Report.md` §7.9；`docs/debt-register.md`（四处不成立） |
| — | 允许 1 人或多人现场讲 | ✅ | — | 已定 **A + D** 两人；D 从第 10 页接手 |

**覆盖结论**：7 个方面全部有对应幻灯片与仓库证据；无遗漏项。

## 3. 分工与时间（**D 从第 10 页开始**）

| 页 | 幻灯片标题 | 讲者 | 累计时间 |
|---|---|---|---|
| 1 | 封面（主张） | **A** | 0:00 |
| 2 | 三个数字：61 / 679 / 33 | A | 0:30 |
| 3 | ① 需求必须可校验 | A | 1:30 |
| 4 | ① 显式取舍 | A | 3:00 |
| 5 | ② 权威链 | A | 4:30 |
| 6 | ② 扩展不改基线 | A | 6:00 |
| 7 | ③ 分工与贡献 | A | 7:30 |
| 8 | ④ 三种角色（盲测） | A | 8:30 |
| 9 | ④ agent 犯的三个错 | A | 9:30 |
| **10** | **⑤ 追溯链 —— D 接手** | **D** | **10:00** |
| 11 | ⑤ FR-012 走到变异 | D | 11:00 |
| 12 | ⑥ 七道门禁 | D | 12:00 |
| 13 | ⑥ 实测拦截（直推被拒） | D | 13:00 |
| 14 | ⑥ 规则页 + PR 列表 | D | 14:00 |
| 15 | ⑦ 三个转折 | D | 14:45 |
| 16 | ⑦ 还不成立的四处 | D | 15:45 |
| 17 | 现场演示（讲解 + 操作） | **D** | 16:45 |
| 18 | 收尾 | **D** | 18:45 |

**交接点**：A 在第 9 页末尾说 *"Now D will take you through traceability, the gates, and what we changed."*
**此后到结束全部由 D 承担**：第 10–16 页讲解、第 17 页演示（D 自己讲解 + 操作）、第 18 页收尾。

---

## 4. 逐页要点（只讲节点与框架）

| 页 | 一句话要点 | 现场可打开的证据 |
|---|---|---|
| 1 | AI 是顾问，代码是执行官 | `README.md` |
| 2 | 覆盖率高 ≠ 测试有效；变异才是证伪 | — |
| 3 | 类型决定必填字段（enforcement / fallback / metric） | `docs/req/requirements.yaml` |
| 4 | 四条取舍：RAG→标签、5% 不对账、V2 只装 4 条、门禁 1 不回填 | `prioritization` 段 |
| 5 | 合规在模型之后，且可否决；`selector/` 不得 import `compliance/` | blueprint 权威图 |
| 6 | V2/V3 均为增量；`policy=None` 与 V1 逐位一致 | `git diff` |
| 7 | 角色先定，系数 1.333 / 0.889×3，平均 1.000 | `Report.md` §3.2 |
| 8 | 写实现的不读测试；唯一让测试变绿的方法是改实现 | `docs/test-approvals.yaml` |
| 9 | 假反例 / 0-job CI / CRLF 哈希——都不是读代码能发现的 | `bug-diary.md` |
| 10 | 需求→矩阵→覆盖表→测试→变异，八个脚本各守一环 | 覆盖表 |
| 11 | FR-012：$14.99→75 分；5%→10% 时 `assert 50 != 75` | `test_v3_pricing.py` |
| 12 | 七道门禁；Gate 1 比时间戳 | `.github/workflows/ci.yml` |
| 13 | 直推被拒的原文；6/7 的真实 PR | `evidence/.../1,2,3.png` |
| 14 | docs/ 不在 CODEOWNERS → 免批准但必须过 CI | 同上 |
| 15 | 三个转折：触发→改动→代价 | `Report.md` §7.9 |
| 16 | 四处不成立：Gate 1 历史、monitor 2/22、子集、5% 口径 | `debt-register.md` |
| 17 | 同一场景两档位结果不同；幂等不二次扣费（D 操作） | 终端 |
| 18 | 不是推荐器，是"让诚实可被检查"的装置（D 收尾） | — |

---

## 5. 现场演示（2 分钟）

```bash
# 1) 同一场景、两个档位 → 结果不同
python -m app --corpus --time-slot afternoon --device desktop --tag family
python -m app --corpus --time-slot afternoon --device desktop --tag student

# 2) 5% 定价 + 竞价 + 幂等（同 request-id 第二次不扣费）
python -m app.cli_v2 --corpus --request-id demo1 --time-slot afternoon --device desktop --tag family --db demo.sqlite3

# 3) 变异（可选，时间紧就不跑）
python scripts/mutation_check.py --list | head
```

**兜底**：`docs/testing/V3-Demo-Screenshots.md` 的 10 张图（离线可放）。

---

## 6. Q&A 预演（全员在场）

| 问题 | 30 秒答案 |
|---|---|
| Gate 1 为什么红？ | V3 测试写于 11-17，具名批准只能之后作出；保留缺口（TD-018），TA-0005 建前向机制 |
| 为什么不用 RAG？ | 向量库破坏零依赖与可复现；13 条被否方案在 `option-ledger.md` |
| 怎么证明测试有效？ | 变异 33/33；第一次跑抓出 4 条"怎么改都绿"的假反例 |
| 5% 有依据吗？ | 演示口径、无对账；真实计费引入税/退款/币种三条失败路径 |
| 贡献怎么算的？ | 角色先定 + 交付物对照 + 团队会议确认，平均 1.0 |
| 如果多两周？ | 统一两套 token 估算；接真实计费；monitor 全覆盖；Gate 1 全绿 |
| agent 写过最差的代码？ | workflow 级 env 导致 0-job；CRLF 哈希；prompt 里塞内部文档路径 |
| 为什么这么多治理？ | 因为绿徽章撒过谎——7 次"成功"、0 个 job |

---

## 7. 准备清单

- [x] 时长 20 分钟（已确认）
- [x] 讲者 A + D（已确认）；**D 从第 10 页接手**
- [x] 幻灯片 18 页（CityU 模板，演讲者备注含讲稿）
- [x] 逐页讲稿 `PRESENTATION-SCRIPT.md`
- [ ] 在**目标机器**上预跑演示命令（`python -m app --corpus` 依赖 2.1 MB 语料，已入库）
- [ ] 离线备份：截图 + 录屏（防现场环境故障）
- [ ] 每人准备 1 个"我做的具体决定"故事（30 秒）
