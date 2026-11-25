# 报告（D6）的硬性要求与现状对照

> **要求出处**：课程材料 `Week1_Project_Requirements.pdf`（工作区根目录）
> 的 **D6 Report** 条目 +「相对贡献」段 +「Submission model」段。
> 本文把原文抄下来并逐条对照仓库现状，避免"凭记忆写报告"。
> 对照日期：2026-11-25

---

## 1. 原文（英文，照抄）

**D6 · Report**

> **D6 Report (as a single markdown .md file)**
> This is the project summary report. The report should list all students' names and student
> numbers, as contain at most **10,000 words** (excluding diagrams) and contain **more than 15
> pages in Point 12 with single-line spacing**. It should present the team's software
> engineering process and how the team optimizes it. It should also include each member's
> **self-reflection** (one short (e.g., **300-500 words**) paragraph per student, **with name and
> student ID**. Cover process quality evidence (requirement volatility, defect trends,
> ambiguity …)
>
> *（PDF 文本层在"ambiguity"之后有字体编码噪声，后续条目需人工对照原文阅读。）*

**相对贡献**

> Your report should include a section of **relative contributions**. The **average
> contribution is 1.0**; students with less contribution can be assigned a lower weight, and
> students with stronger contributions will be assigned a higher weight.

**提交模型**

> Submission model: One repository plus **five annotated agent-session transcripts** and **one
> process report**. The **AI-use log is mandatory** and must be up to date at submission.

---

## 2. 逐条拆解与现状

| # | 要求 | 现状 | 判定 |
|---|---|---|---|
| R-01 | 单一 markdown 文件（`.md`） | `Report.md` 单文件 | ✅ |
| R-02 | 列出**全部学生姓名** | Shen Jiyun（A）已填；B/C/D 仍为占位 | ⚠️ 部分 |
| R-03 | 列出**学号** | 60989886（A）已填；其余缺 | ⚠️ 部分 |
| R-04 | **≤ 10,000 词**（不含图表） | 约 **5,569 词** | ✅ 有余量 |
| R-05 | **> 15 页**，**12pt / 单倍行距** | 已补 5 节至 **7,266 词** + 176 行表格，粗估 16–18 页 | ✅ 待实际渲染确认 |
| R-06 | 每人 **300–500 词**自评 | A 335 / B 362 / C 323 / D 312 词 | ✅ 字数达标 |
| R-07 | 自评**带姓名与学号** | A 已写 Shen Jiyun (60989886)；B/C/D 缺 | ⚠️ 部分 |
| R-08 | 相对贡献表，**平均 1.0** | 表结构在，四行仍 `[TBD]%` | ❌ 缺数据 |
| R-09 | 呈现**软件工程过程 + 如何优化** | §7「Challenges and Rework」覆盖 | ✅ |
| R-10 | **过程质量证据**：需求波动 / 缺陷趋势 / 歧义 | 已新增 §7.8（三张表，含 BUG-001..008 与 OQ 收敛） | ✅ |
| R-11 | 5 份带注释的 agent 会话记录 | `transcripts/` 现 2 份 | ❌ 缺 3 份 |
| R-12 | **AI-use log 必须最新** | `docs/ai-use-log.yaml` 29 条 | ⚠️ 需在提交前再核对一次 |

---

## 3. 两个具体缺口（可量化）

### 3.1 需求波动（requirement volatility）

课程要求"过程质量证据"要有**需求波动**的量化。仓库里有全部原材料，但报告没写：

| 轮次 | 需求条数 | 说明 |
|---|---|---|
| V1 | 22 | 基线（7 个架构元素） |
| V2 | +19 | 竞价 + 原子账本 |
| V3 | +20 | 语料 + 内容分级 + 定价 |
| 合计 | **61** | 见 `docs/req/requirements.yaml` |

可补的一段（含真实数据）：三轮共 61 条、无删除（`evolution_rounds` 全部 `active`）、
V3 一次拒掉 2 条 RAG 方向需求并留下 `requirements-v3-rag-draft.md` 作为否证记录。

### 3.2 缺陷趋势（defect trends）

`docs/bug-diary.md` 有 BUG-001…008，`docs/debt-register.md` 有 TD-001…028。
报告 §7 只挑了 5 个例子讲教训，**没有给出趋势**（何时发现、由谁发现、哪条不变量暴露的缺口）。

可补的一张表：BUG 编号 × 发现轮次 × 暴露的不变量 × 对应新增的检查。

---

## 4. 页数换算（决定还要写多少）

12pt、单倍行距、A4、常规页边距下，英文正文约 **550 词/页**（表格与代码块另计）。

```
当前 5,569 词  ≈ 10 页正文 + 表格/代码约 2 页 ≈ 12 页
要求 > 15 页   →  正文约需 7,000–8,000 词（上限 10,000，仍有余量）
```

因此建议补三节（合计约 2,000 词，都是现成数据）：

1. **§2.7 V2 竞价的完整数据流**（bid sidecar → relevance → 拍卖 → 合规 → 原子结算，配时序表）；
2. **§6.6 实测数据集**（三档通过率 21/10/24、延迟分解、预算 6000→5100 曲线、monitor 输出）；
3. **§7.8 过程质量证据**（需求波动 + 缺陷趋势 + 歧义收敛，即本文件 §3 的两张表）。

---

## 5. 与 `REMAINING-WORK.md` 的对应

| 本文件条目 | 对应任务 |
|---|---|
| R-02 / R-03 / R-07 | RW-09（成员表） |
| R-08 | RW-09（贡献比例） |
| R-05 / R-10 | RW-11（补两节 / 三节） |
| R-06 | RW-10（三份自评，已由成员提交，需确认本人撰写） |
| R-11 | RW-12（transcripts） |
| R-01 / 命名与格式 | RW-14 |
