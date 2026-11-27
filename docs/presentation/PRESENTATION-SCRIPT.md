# 汇报讲稿（20 分钟 · A/D 分工）

> 依据：老师公告的 7 个方面。**幻灯片英文，讲稿英文（现场可直接照读），每页附中文要点。**
> 时长：20 分钟 = A 讲 1–9 页（约 10 分钟）+ D 讲 10–18 页（约 8 分钟）+ 演示 2 分钟。
> 原则：**只讲重要节点、框架、设计**；数字只在能支撑论点时出现。

---

## A 部分（第 1–9 页，约 10 分钟）

### 1. 标题页 · 0:00–0:30

**Say:** Good afternoon. We are group 26 — Shen Jiyun, Gong Yuebin, Zhang Qiyan, Gao Zhechun.
Our project is a scenario-based recommendation engine, and our thesis is one sentence:
**the AI is an advisor, the code is the executive.**

**中文：** 开场只讲一句话主张，不要介绍功能列表。

**Show:** 标题 + 四人姓名学号 + 仓库地址。

---

### 2. 三个数字 · 0:30–1:30

**Say:** Three numbers frame everything that follows. **61** requirements, all machine-readable.
**679** offline tests. **33** mutation injections that prove those tests can actually fail.
The last one is the point: coverage tells you a line ran; mutation tells you whether the
assertion would notice if the line were wrong.

**中文：** 三个数字 + 一句"为什么变异比覆盖率重要"。

---

### 3. ① 需求是怎么变成可验证的 · 1:30–3:00

**Say:** We started with a proposal, not with code. Three rounds added 22, 19 and 20 requirements,
and every one of them is typed. The type decides what else must be written: a functional
requirement must name the exact symbol that implements it, an invariant must name a concrete
fallback, and a quality requirement must carry a metric, a unit and a threshold.
So "we should be fast" is not a requirement; "p95 under 500 ms, measured on the corpus path" is.

**中文：** 关键点是"类型决定必填字段"，这是机器可校验的前提。

**Show:** `docs/req/requirements.yaml` 前 20 行（type / enforcement / fallback / metric）。

---

### 4. ① 取舍必须写出来 · 3:00–4:30

**Say:** The harder half of requirements is what you give up. We use MoSCoW — 58 must, 3 should —
and the registry now carries four explicit tradeoffs. Two examples: we replaced RAG with
deterministic tag matching, and gave up long-tail semantic recall, because a vector store would
break the zero-dependency and reproducibility guarantees. And our 5% ad fee is a demo rule with
no reconciliation — real billing would add tax, refunds and currency as three new failure paths.
Writing the loss down is what keeps the requirement honest.

**中文：** 重点不是"我们做了什么"，而是"我们放弃了什么、为什么"。

---

### 5. ② 架构：一条权威链 · 4:30–6:00

**Say:** Nine elements, one chain. A request is sanitised before it reaches the model, the model
may only choose inside a closed candidate set, and **compliance runs after the model and can veto
it**. In V2 the auction sits between advice and veto; in V3 content grading sits inside the
existing `scene` step, not as a sixth gate. `selector/` is structurally forbidden to import
`compliance/` — the dependency would invert the authority boundary.

**中文：** 讲"顺序"和"结构禁止"，不要说模块清单。

**Show:** blueprint 的权威链图。

---

### 6. ② 扩展而不重写 · 6:00–7:30

**Say:** Each round had to be additive. V2 arrived as a new entry point and a new package; V3
arrived as a ninth element plus an injected policy. `ads/` and `scene/` were not touched in V3,
and when the policy is absent, compliance behaves exactly as it did in V1 — there is a test that
compares the two runs field by field. That is what made three rounds in one codebase survivable.

**中文：** 关键词是 S2"永不删除"，以及"policy=None 与 V1 逐位一致"这条测试。

---

### 7. ③ 团队与贡献 · 7:30–8:30

**Say:** Four roles were fixed before the first line of code. I owned direction, the process
artifacts, and the V1/V3 implementation; Yuebin owned architecture review; Qiyan owned the V2
auction and integration; Zhechun owned independent testing and the evidence package.
Our relative contribution is 33.33% for me and 22.22% each for the others — a 4/3 and 8/9
multiplier, agreed in a team meeting, not computed from hours.

**中文：** 一人一句职责 + 贡献比例的依据（角色 + 交付物，不用工时）。

---

### 8. ④ 人–agent：三种角色 · 8:30–9:30

**Say:** We separated three roles on purpose. The builder may write `src/` and must not read
`tests/`. The tester may write tests and must not touch `src/`. The verifier reads everything
and writes only reports. The reason is a failure we actually hit: an agent asked to fix a failing
test relaxed the assertion. After the split, the only legitimate way to turn a red test green is
to change the implementation.

**中文：** 讲"盲测"这个决定，以及它换来了什么代价（三步变一步）。

---

### 9. ④ agent 犯的错 · 9:30–10:00

**Say:** Three concrete failures. The first mutation run found four "counterexamples" that could
not fail. CI reported success seven times while running zero jobs, because a workflow-level `env`
referenced a context that does not exist there. And our corpus manifest recorded hashes computed
on Windows line endings, so a Linux checkout disagreed with it.
None of these were caught by reading the code.

**中文：** 三个错各一句，不要展开；留给 D 讲改进。

**过渡:** Now D will take you through the traceability, the gates, and what we changed.

---

## D 部分（第 10–18 页，约 8 分钟 + 演示）

### 10. ⑤ 可追溯：一条链 · 10:00–11:00

**Say:** Everything traces through one chain: requirement → trace matrix → coverage map → test →
mutation. Eight scripts enforce different links, so a single broken link cannot hide.
For example, a requirement pointing at a function that no longer exists fails the build.

**中文：** 强调"每一环由不同脚本把守"。

---

### 11. ⑤ 一条需求走通 · 11:00–12:00

**Say:** Take FR-012, "the ad fee is 5% of the game price". The registry points at one function.
The coverage map names three tests. The tests assert concrete numbers — 14.99 dollars becomes
75 cents. And a mutation replaces 5% with 10%: the suite goes red with `assert 50 != 75`.
That is what we mean by traceable: not a link in a document, but a link that can fail.

**中文：** 这是全场最有说服力的一段，要慢讲。

---

### 12. ⑥ 七道门禁 · 12:00–13:00

**Say:** Seven jobs on every pull request: test approval, static analysis, requirements schema,
semantic replay, full regression, mutation verification, and the AI-use log.
Gate 1 is unusual — it compares the approval timestamp with the earliest implementation commit,
so a test cannot be "approved" after it was already written.

**中文：** 七道各半句；重点解释 Gate 1 的时序判定。

---

### 13. ⑥ 门禁真的会拦 · 13:00–14:30

**Say:** Configuration is not evidence, so we measured it. This is a direct push to `main` being
rejected: `push declined due to repository rule violations`, six required checks.
The ruleset page shows the six checks and — deliberately — that the owner is on the bypass list.
And the checks popover shows a real pull request at **6 of 7**: regression is red, so it cannot
merge. Note which gate is red: not the approval gate, the regression gate.

**中文：** 三张图分别是"被拒""规则""6 绿 1 红"，讲完主动说 bypass 的取舍。

**Show:** `evidence/v3/v3-20261125-github-gates/{1,2,3}.png`。

---

### 14. ⑦ 三个转折 · 14:30–15:30

**Say:** Three things changed how we worked. Four decorative counterexamples turned mutation
verification into a blocking gate. The zero-job CI incident made "count the jobs" the first step
of any CI investigation. And the same rule appearing in three places forced a single source of
truth plus a documentation audit. Each change cost something — mutation adds about 50 seconds to
every run — and we kept it because its failure mode is silent.

**中文：** 每个转折一句"触发 → 改动 → 代价"。

---

### 15. ⑦ 还不成立的地方 · 15:30–16:30

**Say:** We also want to be explicit about what does not hold. Gate 1 is red for the V3 history:
those tests were written before the approval mechanism existed, and we chose to record the gap
rather than backdate a timestamp. Runtime monitoring is registered for 22 metrics but only two
are collected. The corpus is a 5,000-row subset of 25,899. And the 5% fee is a demo rule.
All four are in the debt register with re-open conditions.

**中文：** 主动承认四件事，比被问出来强。

---

### 16. 现场演示 · 16:30–18:30

**Say:** Two minutes, three commands. First the same scene with two different audience tags —
the family tier returns an ad, the student tier rejects most candidates, and the detail line
names the tier and the blocked label. Then the V2 path: a 300-cent bid derived from a 59.99
game, and a repeated request id that returns the same result without charging twice.

**中文：** 先跑命令再解释，别边跑边说；准备好失败时的备用截图。

---

### 17. 收尾 · 18:30–19:30

**Say:** Our contribution is not the recommendation engine — a five-step gate and a
pay-as-bid auction are simple. It is the arrangement that keeps them honest: requirements that
fail the build when unimplemented, invariants that fail the build when unfalsifiable, tests the
implementation author may not read, and a gate that reports its own historical failure.
That is the one sentence we would like you to take away.

**中文：** 收尾回到开头那句话，不要再加新信息。

---

## Q&A 预演（5 分钟，全员在场）

| 问题 | 30 秒答案 |
|---|---|
| Gate 1 为什么红？ | V3 测试写于 11-17，命名批准只能之后作出；我们保留缺口（TD-018）并建立 TA-0005 前向机制 |
| 为什么不用 RAG？ | 向量库破坏零依赖与可复现；13 条被否方案在 `option-ledger.md` |
| 怎么证明测试有效？ | 变异 33/33；第一次跑抓出 4 条"怎么改都绿"的假反例 |
| 5% 有依据吗？ | 演示口径、无对账；真实计费引入税/退款/币种三条失败路径 |
| 贡献怎么算的？ | 角色先定 + 交付物对照 + 团队会议确认；平均 1.0 |
| 如果多两周？ | 统一两套 token 估算；接真实计费；monitor 全覆盖；Gate 1 全绿 |
| agent 写过最差的代码？ | workflow 级 env 导致 0-job；CRLF 哈希；prompt 里塞了内部文档路径 |
| 为什么这么多治理？ | 因为绿徽章撒过谎——7 次"成功"、0 个 job |

---

## 讲者分工速查

| 页 | 内容 | 讲者 | 累计时间 |
|---|---|---|---|
| 1–2 | 主张 + 三个数字 | A | 1:30 |
| 3–4 | 需求与取舍 | A | 4:30 |
| 5–6 | 架构与扩展 | A | 7:30 |
| 7 | 团队与贡献 | A | 8:30 |
| 8–9 | 人–agent 与 agent 的错 | A | 10:00 |
| 10–11 | 可追溯 + 一条需求 | D | 12:00 |
| 12–13 | 七道门禁 + 实测拦截 | D | 14:30 |
| 14–15 | 转折 + 仍不成立 | D | 16:30 |
| 16 | 现场演示 | D（A 操作终端） | 18:30 |
| 17 | 收尾 | A | 19:30 |
| — | Q&A | 全员 | 20:00+ |
