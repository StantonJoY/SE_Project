# 汇报讲稿（20 分钟 · A/D 分工）

> 依据：老师公告的 7 个方面。**幻灯片英文，讲稿英文（现场可直接照读），每页附中文要点。**
> 时长：20 分钟 = A 讲 1–11 页（约 10:40）+ D 讲 12–20 页（约 8:00）+ Q&A 缓冲。
> 主线：**不是"最终长什么样"，而是每一轮"为什么改、怎么设计、放弃了什么"。**

---

## A 部分（第 1–11 页，约 10 分 40 秒）

### 1. 封面 · 0:00–0:30

**Say:** Good afternoon. We are group 26. The engine is ours, but the story we want to tell is how
three rounds of requirements changed it — each round triggered by something the previous round
could not do.

**中文：** 开场就把主线抛出来：三轮迭代，每轮都由上一轮做不到的事触发。

---

### 2. 三个数字 · 0:30–1:15

**Say:** Three numbers. **61** requirements across three rounds — 22, 19, 20 — and none deleted.
**679** tests, because every round re-runs all previous suites. **33** mutation injections that
prove those tests can fail. The interesting number is 61: requirements were not written once;
each round added a slice, and the previous slices stayed in force.

**中文：** 强调 22/19/20 是累加、不是替换。

---

### 3. 三轮，三个不同的问题 · 1:15–3:00

**Say:** Here they are side by side. **V1** had to prove an AI component could be constrained at
all — so we chose seven elements, a closed candidate set, a five-step compliance gate, and fourteen
hand-written ads. **V2** came from a gap: recommendations were free — no budget, no competition,
no persistence — so we added an auction, a ledger and idempotency, and moved the AI's role from
"chooses" to "advises". **V3** came from credibility: fourteen hand-written ads made every
recommendation a toy, so we added a real corpus, content grading and pricing.
Read the last column, not the middle one: each round had to say what it gave up.

**中文：** 全场最重要的一页。先横着讲三轮，再竖着指"放弃"那一列；不要逐个展开细节。

**Show:** 表格第 4 列（What we gave up）。

---

### 4. 第二轮：竞价把什么写进了需求 · 3:00–4:20

**Say:** Round two is the clearest example of design following requirements. The trigger was a
gap, not a feature request: V1 had no notion of money. The requirement said "one winner, budgets
persist, no double charge". That forced four design decisions. Money as **integer cents**, because
floating point in a ledger is a bug waiting to happen. **One transaction** for budget, request and
audit, because partial writes are how you get free ads. **Pay-as-bid, not Vickrey** — second price
is theoretically better and practically harder to explain and easy to game. And compliance runs
**after** the auction: the money is computed before the veto, committed after it.
What we gave up: second-price incentives, and free retries.

**中文：** 这是"需求 → 设计"最典型的例子，四个决定各一句，最后点"放弃"。

---

### 5. 第三轮：真实数据改的是需求，不只是数据 · 4:20–5:45

**Say:** Round three looks like "plug in a dataset". It was not. A read-only corpus with 25,899
rows, a deterministic top-K, and content grading — because the corpus contains violent content that
the original 14 ads never had. The constraint was that the `Ad` schema must not change, so the extra
facts travel in a side channel. Grading lives **inside** the existing scene step, not as a sixth
gate, so the compliance chain keeps its five steps. And with no policy injected, compliance behaves
exactly as V1 — there is a test that compares both runs field by field.
What we gave up: RAG, four-fifths of the corpus, and real billing.

**中文：** 三个"不是"：不是换数据；不是加第六步；不是改 schema。然后说放弃。

---

### 6. 每轮都必须可校验，并且说出代价 · 5:45–6:45

**Say:** Two rules made three rounds possible. First, type decides what else must be written:
a functional requirement names the symbol, an invariant names a fallback, a quality requirement
carries a metric. Second, every round publishes its losses — four tradeoffs sit in the registry
next to the requirements they constrain. The one I want to point at is the last: Gate 1 is red for
the V3 history, and we did not backdate a timestamp to make it green.

**中文：** 把"取舍"从口头承诺变成登记表条目；最后一行是为后面第 18 页埋的伏笔。

---

### 7. 一条权威链 · 6:45–7:45

**Say:** Nine elements, one chain. A request is sanitised before it reaches the model, the model may
only choose inside a closed candidate set, and compliance runs after the model and can veto it.
`selector/` is structurally forbidden to import `compliance/` — that dependency would invert the
authority boundary.

**中文：** 只讲顺序和"结构上禁止"，不列模块。

---

### 8. 三轮，一套代码：只扩展，不替换 · 7:45–8:30

**Say:** Each round had to be additive. V2 arrived as a new entry point and package; V3 as a ninth
element plus an injected policy. `ads/` and `scene/` were not touched in V3 — you can check with
`git diff`.

**中文：** 关键词是"增量"和"可验证"（git diff）。

---

### 9. 四个角色 · 8:30–9:10

**Say:** Four roles were fixed before the first line of code. I owned direction, process artifacts
and the V1/V3 implementation; Yuebin architecture review; Qiyan the V2 auction and integration;
Zhechun independent testing and evidence. Contribution is 33.33% for me and 22.22% each — agreed
in a team meeting from roles and artifacts, not hours.

**中文：** 一人一句 + 一句"依据"。

---

### 10. 三种角色：写实现的不能读测试 · 9:10–9:55

**Say:** We separated three roles on purpose. BUILD writes `src/` and must not read `tests/`.
TESTER is the mirror image. VERIFY reads everything and writes only reports. The reason is a
failure we hit: an agent asked to fix a red test relaxed the assertion.

**中文：** 讲"为什么"，不要讲"我们很严格"。

---

### 11. agent 犯的错 · 9:55–10:40

**Say:** Three concrete failures. The first mutation run found four counterexamples that could not
fail. CI reported success seven times while running zero jobs. And our manifest hashed files with
Windows line endings, so a Linux checkout disagreed. None of these were found by reading the code.

**中文：** 三个错各一句，收尾"读代码发现不了"。

**过渡:** D will take you through traceability, the gates, and what we changed.

---

## D 部分（第 12–20 页，约 8 分钟）

### 12. 可追溯：一条链（D 接手） · 10:40–11:30

**Say:** Everything traces through one chain: requirement → trace matrix → coverage map → test →
mutation. Eight scripts each own one link, so a single broken link cannot hide. A requirement
pointing at a deleted symbol fails the build.

**中文：** 强调"每一环由不同脚本把守"。

---

### 13. FR-012：从一句话到一次变异 · 11:30–12:20

**Say:** Take FR-012, "the fee is 5% of the price". The registry points at one function; the
coverage map names three tests that assert numbers — $14.99 becomes 75 cents. And a mutation
replaces 5% with 10%: the suite goes red with `assert 50 != 75`. Traceable means a link that can
fail.

**中文：** 全场最有说服力的一段，慢讲。

---

### 14. 七道门禁 · 12:20–13:15

**Say:** Seven jobs on every pull request: test approval, static analysis, requirements schema,
semantic replay, full regression, mutation verification, AI-use log. Gate 1 is the unusual one —
it compares the approval timestamp with the earliest implementation commit, so a test cannot be
approved after it was written.

**中文：** 七道各半句，重点解释 Gate 1 的时序判定。

---

### 15. 门禁真的会拦 · 13:15–14:10

**Say:** Configuration is not evidence, so we measured it. This is a direct push being rejected:
`push declined due to repository rule violations`, six required checks. And the checks popover shows
a real pull request at **6 of 7** — regression red, so it cannot merge. Note which gate is red: not
the approval gate, the regression gate.

**中文：** 讲完主动说 bypass 的取舍（下一张）。

**Show:** `evidence/v3/v3-20261125-github-gates/{1,2,3}.png`

---

### 16. 规则页与 PR 列表 · 14:10–14:50

**Say:** Two things to point at. The ruleset requires six checks on the default branch, and the
owner sits on the bypass list — disclosed, not hidden. The PR list shows sixteen merged and two
open, both at six of seven. The consequence is in the bottom line: `docs/` is not a Code-Owner path,
so documentation needs no approval — but never merges without green CI.

**中文：** 诚实披露 bypass；把"文档免审但必须过 CI"讲清楚。

---

### 17. 三个转折 · 14:50–15:45

**Say:** Three things changed how we worked. Four decorative counterexamples turned mutation
verification into a blocking gate. The zero-job incident made "count the jobs" step one of any CI
investigation. And the same rule in three places forced a single source of truth plus a
documentation audit. Each change cost something — mutation adds about 50 seconds per run — and we
kept it because its failure mode is silent.

**中文：** 每个转折一句"触发 → 改动 → 代价"。

---

### 18. 还不成立的地方 · 15:45–16:35

**Say:** Four things do not hold. Gate 1 is red for the V3 history — we recorded the gap instead of
backdating. Monitoring: 22 metrics registered, 2 collected. Corpus: 5,000 of 25,899 rows. And the
5% fee is a demo rule with no reconciliation. All four are in the debt register with re-open
conditions.

**中文：** 主动承认，承接第 6 页的伏笔。

---

### 19. 现场演示（D 讲 + D 操作） · 16:35–18:35

**Say:** Two minutes, three commands. First the same scene with two audience tags — the family tier
returns an ad, the student tier rejects most candidates and names the blocked label. Then the V2
path: a 300-cent bid from a $59.99 game, and a repeated request id that returns the same result
without charging twice.

**中文：** 自己操作、自己讲解；先跑再解释；准备好备用截图。

**底部一句:** Before I hand back — this is the same system the report describes, running on the
delivered commit.

---

### 20. 收尾（D） · 18:35–19:10

**Say:** Our contribution is not the recommendation engine. It is the arrangement that keeps it
honest: requirements that fail the build when unimplemented, invariants that fail the build when
unfalsifiable, tests the implementation author may not read, and a gate that reports its own
historical failure.

**中文：** 收尾回到开头那句话，不再加新信息。

---

## Q&A 预演（19:10–20:00 缓冲 + 提问）

| 问题 | 30 秒答案 |
|---|---|
| 为什么第二轮不做次价（Vickrey）？ | 理论更优但难解释、易被策略化；pay-as-bid 可解释、可审计、无策略空间 |
| V3 为什么不改 Ad schema？ | 改 schema 会触碰 V1/V2 的契约与全部既有测试；旁路 facts 让 V1 代码零改动 |
| 内容分级为什么不做第六步？ | 第五步已握有场景与品类；加第六步会让"五步"契约与 36 条不变量全部重写 |
| Gate 1 为什么红？ | V3 测试写于 11-17，具名批准只能之后作出；保留缺口（TD-018），TA-0005 建前向机制 |
| 为什么不用 RAG？ | 向量库破坏零依赖与可复现；13 条被否方案在 `option-ledger.md` |
| 怎么证明测试有效？ | 变异 33/33；第一次跑抓出 4 条"怎么改都绿"的假反例 |
| 5% 有依据吗？ | 演示口径、无对账；真实计费引入税/退款/币种三条失败路径 |
| 贡献怎么算的？ | 角色先定 + 交付物对照 + 团队会议确认；平均 1.0 |
| 如果多两周？ | 统一两套 token 估算；接真实计费；monitor 全覆盖；Gate 1 全绿 |

---

## 讲者分工速查

| 页 | 内容 | 讲者 | 累计时间 |
|---|---|---|---|
| 1–2 | 主张 + 三个数字 | A | 1:15 |
| 3 | 三轮对照表（迭代动因） | A | 3:00 |
| 4 | 第二轮：竞价 → 需求 | A | 4:20 |
| 5 | 第三轮：真实数据 → 需求 | A | 5:45 |
| 6 | 可校验 + 四条取舍 | A | 6:45 |
| 7–8 | 权威链 + 只扩展不替换 | A | 8:30 |
| 9 | 团队与贡献 | A | 9:10 |
| 10–11 | 三种角色 + agent 的错 | A | 10:40 |
| **12–16** | **可追溯 / FR-012 / 七门禁 / 实测拦截 / 规则页（D 接手）** | **D** | 14:50 |
| 17–18 | 三个转折 + 仍不成立 | D | 16:35 |
| 19 | 现场演示（讲解 + 操作） | D | 18:35 |
| 20 | 收尾 | D | 19:10 |
| — | Q&A | 全员 | 20:00+ |

> 交接点固定在**第 12 页**：A 讲完第 11 页说 “D will take you through traceability, the gates,
> and what we changed.” 此后到结束全部由 D 承担。
