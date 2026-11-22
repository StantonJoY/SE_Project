# Scenario-Based Ad Recommendation Engine

## Team Delivery Report — Rounds V1 to V3

| | |
|---|---|
| Repository | `github.com/StantonJoY/SE_Project` |
| Delivered commit | `8b5a17a` (merge of PR #3, `v3` → `main`), plus `a9c79d8` (branch-protection preparation) |
| Report version | 1.0 — 2026-11-22 |
| Team | [MEMBER A] (PM, architecture/AI), [MEMBER B], [MEMBER C], [MEMBER D] |
| Submission file | `[STUDENT_ID].md` |

---

## Abstract

We built a scenario-based advertising recommendation engine in three rounds and governed
the whole construction with machine-checkable artifacts rather than prose. The system's
central design rule is that **the AI is an advisor and the code is the executive**: a
language model may only choose inside a closed candidate set, and every display decision
is made by a deterministic five-step compliance pipeline that the model cannot bypass. V1
delivered seven architectural elements end to end. V2 added a single-winner, pay-as-bid
auction with an atomic SQLite ledger. V3 replaced the fourteen hand-written advertisements
with a 5,000-row Steam corpus, added scene-tiered content grading, and derived bids from
game prices at 5%.

The repository holds 61 requirements, 36 invariants, 679 offline tests, 33 mutation
injections that prove those tests can actually fail, 57 fixed evaluation cases, and seven
CI gates. This report explains what we built, how humans and AI agents divided the work,
what the verification actually proves, and — at equal length — where it does not.

---

## 1. Requirements and Specification

### 1.1 A single machine-readable registry

All requirements live in `docs/req/requirements.yaml` and are validated against
`docs/req/req-schema.json` on every commit. The registry currently holds **61 requirements**:
14 functional, 8 quality, 6 governance, 3 security, 2 performance, 2 cost, and **26
invariants**. Requirements are typed, and the type carries obligations the validator
enforces:

| Type | Mandatory extra field | Why |
|---|---|---|
| `functional` / `quality` / … | `enforcement` — the code symbol that implements it | Prevents "documented but not implemented" |
| `invariant` | `fallback` — what the system does when violated | Forces fail-closed thinking, not just detection |
| `quality` / `performance` / `cost` | `metric {name, unit, threshold, direction}` | Makes "fast enough" checkable instead of rhetorical |

`scripts/validate_requirements.py` performs four checks in one pass: JSON-Schema
conformance, uniqueness of IDs, bidirectional consistency between *enforcement* pointers and
real symbols, and the presence of the type-specific fields above. A requirement that names
a non-existent function fails the build.

### 1.2 Three rounds, one ID space

The three rounds added 22 (V1), 19 (V2) and 20 (V3) requirements. We deliberately kept a
single ID space with family prefixes (`FR-`, `ARCH-`, `NFR-SAFETY-`, `SEC-`, `GOV-`,
`NFR-QA-`, `NFR-PERF-`, `NFR-COST-`) rather than inventing `V3-*` identifiers: the validator
derives each requirement's architectural family from its prefix, so a new prefix would have
silently escaped family-level checks. This was discovered when the first V3 draft used
`REQ-V3-SE-01` and the validator rejected it; we renumbered into the existing families and
recorded the episode in the AI-use log.

### 1.3 Architecture-significant requirements first

27 of the 61 requirements are architecture-significant (ASR). They were written before the
corresponding design, and each one is traceable to an ADR decision. For example
`REQ-ADS-ARCH-013` ("the corpus must not enter the advertisement contract") produced ADR-006
D3 (projection bypass), and `REQ-ADS-NFR-SAFETY-008/009/010` (content grading) produced
ADR-006 D4 (grading lives inside the existing `scene` step, not as a sixth step).

### 1.4 Open questions were closed, not carried

Ten open questions (`OQ-001`…`OQ-010`) were resolved during the rounds and are recorded with
their resolutions. Two that shaped the delivery:

- **OQ-005** — how large the fixed evaluation set must be. Resolved as "at least 20 cases per
  round, with negatives explicitly counted separately".
- **OQ-009** — whether explanations must state *why this one*. Resolved as yes for V1, and
  the explanation path is structurally isolated from the decision path (ADR-001).

### 1.5 What "done" means

A requirement is not done when code exists. It is done when the trace matrix names the
component, the coverage map names at least one test, and — for invariants — a mutation entry
proves that breaking the implementation turns that test red. Section 5 walks one requirement
through that chain end to end.

---

## 2. Architecture and Integration

### 2.1 Nine elements, one authority chain

The system has nine architectural elements, each mapping to exactly one package (enforced by
structural constraint S1 in `scripts/fitness_functions.py`):

| Element | Package | Responsibility |
|---|---|---|
| ① Ad material | `src/ads/` | Schema, loading, banned words, scene filtering |
| ② Scene | `src/scene/` | Parse and validate the request scene |
| ③ Compliance | `src/compliance/` | Five-step deterministic gate — **final authority** |
| ④ Selector | `src/selector/` | Prompt assembly, model client, strict output parsing, explanation |
| ⑤ App | `src/app/` | Orchestration, sanitize gate, fail-closed degradation, CLIs |
| ⑥ Render | `src/render/` | Two-shape output contract and validation |
| ⑦ Audit | `src/audit/` | Append-only JSONL audit and the monitor registry |
| ⑧ Evaluation | `eval/` | Fixed case sets and deterministic replay |
| ⑨ Corpus | `src/corpus/` | Read-only Steam corpus, projection, deterministic top-K, pricing |

The authority chain is the point of the design:

```
request → sanitize (pre-model) → candidate assembly → LLM advice (advisory only)
        → [V2: deterministic auction] → compliance (FINAL AUTHORITY) → render → audit
```

`src/selector/` is forbidden to import `src/compliance/`; the reverse dependency would
invert the authority boundary. This is checked structurally, not by convention.

### 2.2 V1: five steps, fail-closed

`compliance.pipeline.run_compliance` executes exactly five checks in a fixed order:

```
output_exists → banned_words → banned_check → category → scene
```

Any failure returns `no_ad` with a reason code; there is no "retry with the second-best
candidate" path, because that would convert a hard gate into a soft preference. The order
itself is an invariant (`INV-V3-005`) with a mutation entry that reorders the steps and
proves the ordering test fails.

### 2.3 V2: auction between advice and authority

V2 inserts a deterministic auction *after* relevance advice and *before* compliance. Bids are
integer cents, the winner is the highest `relevance × bid`, ties break on ascending `ad_id`,
and the charge equals the winner's own bid (pay-as-bid). Budget, result and audit row are
written in one SQLite transaction, and `request_id` makes every request idempotent. A
fingerprint conflict returns `request_conflict` without charging.

The important architectural property is that the auction cannot weaken the gate: compliance
still runs afterwards on the winner, and a rejected winner yields `no_ad` even though money
was already computed. The ledger commit happens only after compliance approves.

### 2.4 V3: real corpus without breaking the contract

V3 replaced hand-written material with 5,000 real Steam records. Three decisions kept the
existing contract intact:

1. **Projection bypass (ADR-006 D3).** Corpus rows never enter the `Ad` schema directly.
   `corpus.projection.corpus_to_ad` emits a legal `Ad` with `ad_id = ad_<item_id>`; everything
   that does not fit (content descriptors, required age, price) travels in a side-channel
   `CorpusFacts` object. `AD_SCHEMA` is unchanged, and a test loads a raw corpus row through
   `AdRepository.load` to prove extra fields are still rejected.
2. **Content grading inside the existing step (D4).** Grading is not a sixth compliance step.
   `ContentPolicy` is injected into `check_scene`; when `policy=None`, behaviour is bitwise
   identical to V1 (proven by a dedicated equivalence test). This preserves the V1 contract
   while allowing V3 scenes to be graded.
3. **Pricing as a single source (D5).** `bid = max(1, round(price × 5%))` and
   `budget = bid × 20` live only in `src/corpus/pricing.py`. A static test walks `src/corpus`,
   `src/app` and `scripts` and fails if the literal `0.05` appears anywhere else.

### 2.5 Integration contracts

Interface contracts are written down as ordering guarantees, not as "caller should":

| Caller | Callee | Guarantee |
|---|---|---|
| `app.sanitize` | selector client | Injection patterns are neutralised before the model is called |
| `app.pipeline` | `selector.context` | Six-layer assembly respects the token budget; compaction never drops layer 2, and constraints are re-injected afterwards |
| `app.pipeline` | `selector.parser` | Strict JSON; malformed output never reaches a decision |
| `app.pipeline` | `compliance.run_compliance` | Runs before any display, with FINAL AUTHORITY |
| `app.pipeline` | `selector.explanation` | Explanation is read-only; it may never write `ad_id` |
| `app.pipeline` | `audit.store` | Exactly one audit record per request; the decision path never reads audit history |

The re-injection rule is not theoretical: course material reports constraint satisfaction
dropping from 98% to 72% after compaction pushes instructions into low-attention positions.
Our assembler re-injects the constraint block unconditionally, and a test asserts the marker
is present after compaction.

### 2.6 Extension without deletion

Structural constraint S2 forbids deleting a superseded element: V2 had to be added alongside
V1 (`cli_v2`, `pipeline_v2`) rather than mutating V1 behaviour, and V3 had to arrive as a new
element plus an injected policy rather than as a rewrite of compliance. `git diff` for V3
shows `bidding/`, `ads/` and `scene/` untouched.

---

## 3. Team Organization and Contributions

### 3.1 Roles

| Member | Role | Primary scope |
|---|---|---|
| [MEMBER A] | PM / architecture / AI | Theme and iteration direction, process-artifact system, V1 and V3 implementation |
| [MEMBER B] | Architecture / AI review | Requirements and ADR review, prompt and model decisions |
| [MEMBER C] | Application / integration | V2 auction and ledger integration, CLIs |
| [MEMBER D] | Quality / governance | Independent test execution, evidence packaging, gate verification |

### 3.2 Relative contribution

The course asks for a relative-contribution table whose **average is 1.0**. We report both the
share and the derived factor, because a factor alone forces the reader to reverse-engineer it:

| Member | Share | Relative factor | Note |
|---|---|---|---|
| [MEMBER A] | [TBD]% | [TBD] | PM; V1 and V3 implementation; process-artifact system |
| [MEMBER B] | [TBD]% | [TBD] | |
| [MEMBER C] | [TBD]% | [TBD] | |
| [MEMBER D] | [TBD]% | [TBD] | |
| **Average** | **100%** | **1.00** | Σfactor / 4 = 1.0 |

*Factor = share × 4. The four members must agree on the shares before submission; the
placeholder row values are not filled in by an agent.*

### 3.3 Self-evaluations

> **Note to the reader:** the course requires each member's self-evaluation to be written by
> that member. The paragraph below is a draft prepared by [MEMBER A] from the repository
> record and must be restated in the member's own words before submission.

#### MEMBER A — self-evaluation (draft, 300–500 words)

I was the team's PM, and my work fell into three buckets: direction, system, and code.

**Direction.** From round one I fixed the project's thesis: the AI is an advisor and the code
is the executive. The model may only choose inside a closed candidate set, and whether anything
is displayed is decided by a deterministic compliance pipeline. That single boundary kept the
later rounds honest — the V2 auction and the V3 corpus integration both had obvious ways to
bypass the gate, and both were rejected on the same grounds.

**System.** I built the process artifacts that make the claims checkable: a 61-entry
requirement registry, 36 invariants with explicit fallbacks, ADRs for every protected path, a
trace matrix, six CI gates plus mutation verification, an AI-use log, and named human test
approvals. These are not decoration. The first mutation run found four "counterexamples" that
could not fail: they asserted behaviour that the implementation would satisfy even when
deliberately broken. Separately, CI had reported success seven times while in fact running
zero jobs, because `${{ runner.temp }}` was referenced at workflow level where the runner
context does not exist; the failure was found by reading logs rather than trusting green
badges.

**Code.** I implemented V1's seven architectural elements and V3's corpus integration. The
finding I am most satisfied with is the union rule in content grading: across the full 25,899
record corpus, 8,877 records have empty `descriptors` but non-empty `warnings`, so a
descriptor-only filter would have admitted roughly a third of the violent content.

**Working with agents.** My early habit was to let one agent write both implementation and
tests, which predictably produced tests shaped around the implementation's behaviour. We
replaced it with a blind protocol: tests are written first and must fail, a named human
approves them, and only then is the implementation written. Gate 1 still reports a red for the
V3 history because those tests were written before the protocol existed. I chose to report that
gap rather than backdate a timestamp.

#### MEMBER B — self-evaluation

> **[To be written by MEMBER B. Do not submit this placeholder.]**

#### MEMBER C — self-evaluation

I was responsible for iterating on and extending V2. Building on V1, I used Codex agents to develop a deterministic, single-winner advertising auction and persistent budget management. The model provided relevance scores, while the code ranked candidates using relevance multiplied by bid, resolved ties by advertisement ID, and charged the winner its own bid. Compliance checks retained the final authority to reject an advertisement before charging. SQLite ensured that budget updates, request results, and audit records were committed together, while request replay prevented duplicate charges. I also used the agents to check the implementation against the course specification and V2 handover document, run regression tests and fixed-case evaluations, organize verification materials, and prepare the GitHub submission. A subsequent CI configuration fix enabled GitHub Actions to run the checks. The missing evidence of pre-implementation human test approval remained documented as a process limitation.

This group assignment differed from those in other courses and offered a fresh approach to project work. However, as AI becomes more capable, I feel that users’ interventions have a diminishing influence on the results of relatively straightforward tasks. During my V2 work, I tried different prompts and found little difference in the outputs. Nevertheless, I deliberately adopted more detailed conversational prompts partly to improve the presentation and make the amount of work involved more visible. This made me question how effectively the length or detail of a conversation demonstrates a student’s contribution. I considered using a weaker agent or model, but then wondered why I should choose an older, less capable tool when a better one was available simply to demonstrate my own ability. To me, that would be like applying an outdated standard after the circumstances had changed. My greatest gain from this project was the thinking that took place while using AI. Following the implementation, asking questions about its behavior, and examining the verification results helped me understand the project’s components and how they worked together.

#### MEMBER D — self-evaluation

> **[To be written by MEMBER D. Do not submit this placeholder.]**

---

## 4. Human–AI Interaction

### 4.1 Roles are separated on purpose

`AGENTS.md` defines three roles with different read and write permissions: BUILD (may write
`src/`, must not read `tests/`), VERIFY (reads everything, writes only reports) and TESTER
(may write `tests/`, must not write `src/`). The blindness rule is deliberate: an agent that
can read the tests will eventually edit them to match a broken implementation, and the suite
will stay green while the invariant is violated.

This is not hypothetical for us. Before the rule, an agent's fix to a failing test consisted
of relaxing the assertion. After the rule, the only legitimate way to make a red test green is
to change the implementation.

### 4.2 What the human approval mechanism actually does

`docs/test-approvals.yaml` records named human approvals of test files, and
`scripts/check_test_approval.py` is a blocking CI gate. It checks two layers: structure
(every record has real requirement IDs, real test paths, a non-placeholder approver) and
**timing** — the approval must predate the earliest implementation commit in the change set.

The timing layer is the interesting one, because it is satisfied by evidence rather than
assertion. Our final round produced the inversion in a real commit sequence:

| Time | Commit | Content |
|---|---|---|
| 19:52:16 | `38997ca` | A failing test for UTF-8 output, plus `TA-0005` (the approval) |
| 19:53:34 | `3f230a8` | The implementation that makes it pass |

The test was red at the moment it was approved. That is the course's "approved before
implementation" requirement expressed as an observable fact rather than a claim.

### 4.3 Where the mechanism is red, and why we left it red

`TA-0005` is our first genuine pre-approval. Everything written before it — the V2 tests and
the V3 body of tests — was implemented in the same sessions that wrote it, so no honest
approval can predate it. We recorded the situation as `TA-0006`: an explicit **post-hoc
acceptance** naming the human, the 17 test files and 34 requirements, with a note stating that
it does not satisfy the timing rule.

The result is that Gate 1 stays red on the V3 merge commit. We left it red on purpose. The two
alternatives were to backdate a timestamp or to weaken the checker, and both would have turned
the gate into decoration at exactly the moment it mattered most.

### 4.4 Prompt changes are governed like code

The model prompt is a versioned artifact (`ctx-v1.1`, `relevance-v2.2`). Any prompt or auction
change triggers the semantic-evaluation gate, which replays the fixed case sets. When we
aligned the prompt with the new corpus — adding scene semantics, forbidding the use of outside
knowledge about the works, and removing an internal documentation path that was being fed to
the model — we bumped both versions and re-ran all three replay suites.

We were explicit about what that proves and what it does not: the offline replay uses a mock
client that selects the lexicographically smallest candidate, so it **cannot** show that a
prompt produces better choices. The independent test team later ran a real model against the
new prompt: 30/30 structurally valid, 5/5 title-bait cases and 5/5 known-title cases selected
the tag-matching candidate rather than the famous one. That is the first evidence we have that
the "no outside knowledge" clause works.

### 4.5 What the agent got wrong

| Episode | What happened | What caught it |
|---|---|---|
| Decorative counterexamples | Four tests could not fail under deliberate breakage | Mutation verification (first run) |
| Silent CI | Seven runs reported "no jobs" between 2026-10-11 and the fix | Reading the job list, not the badge |
| CRLF-hashed manifest | Corpus hashes were computed on Windows line endings, so a LF checkout disagreed | Independent test run on another machine |
| Prompt without scene semantics | The model saw `family` as an opaque token | Review of the rendered prompt |
| Corrupted identifiers | First V3 draft used an ID prefix the validator rejects | `validate_requirements.py` |

Each of these is recorded in `docs/bug-diary.md` or `docs/debt-register.md` with the invariant
gap it exposed.

### 4.6 What the human caught that the agent did not

The most useful human interventions were structural rather than syntactic:

- insisting that a green badge is not evidence, which led to the CI job-count check;
- refusing to let the assistant write the teammate self-evaluations or approve its own tests;
- deciding to merge the V3 branch with Gate 1 red rather than manufacture a timestamp;
- requiring that every claim in the handover be backed by a command the reader can run.

---

## 5. Traceability

### 5.1 The chain

```
requirements.yaml  →  trace-matrix.md  →  acceptance-coverage-map.yaml  →  tests  →  mutation
     (what)              (which part)          (which evidence)          (proof)   (proof of proof)
```

Every link is machine-checked by a different script, so a single broken link cannot hide:

| Script | What it would catch |
|---|---|
| `validate_requirements.py` | Unknown ID, duplicate, missing fallback, enforcement pointing at nothing |
| `scripts/fitness_functions.py` | Element/module drift (S1), deletion of an element (S2), missing ADR references (S3), missing round criteria (V1–V4) |
| `check_safety_paths.py` | A protected path changed without an accompanying ADR |
| `check_test_approval.py` | Tests changed without a prior named human approval |
| `check_semantic_eval.py` | Prompt/auction changes without replay |
| `check_ai_use_log.py` | AI-assisted code changes not recorded |
| `check_repo_completeness.py` | Files on disk that never entered the repository |
| `scripts/mutation_check.py` | A counterexample test that cannot fail |

### 5.2 One requirement, walked end to end

Take `REQ-ADS-FR-012` ("advertising fee is 5% of the game price"):

1. **Registry** — `docs/req/requirements.yaml` declares it functional, with `enforcement:
   ["corpus.pricing.bid_cents_from_price", "scripts.build_bids_v3.build_bids"]`.
2. **Trace matrix** — `docs/architecture/trace-matrix.md` maps it to the corpus element and to
   the pricing module.
3. **Coverage map** — `docs/code-governance/acceptance-coverage-map.yaml` names three evidence tests:
   `test_bid_is_five_percent_of_price`, `test_free_game_bids_one_cent`,
   `test_bids_sidecar_matches_corpus_prices`.
4. **Tests** — those tests assert concrete numbers ($14.99 → 75 cents, $59.99 → 300, free → 1)
   and recompute the whole sidecar from the corpus.
5. **Mutation** — `MUT-V3-BID-TEN-PERCENT` replaces the 5% ratio with 10%; the suite goes red
   with `assert 50 != 75`, which is what makes the coverage claim meaningful.
6. **Invariant** — `INV-V3-007` (single derivation source) is additionally checked statically:
   the literal `0.05` may not appear outside `src/corpus/pricing.py`.

The same walk works for any requirement; the acceptance criterion for this report was that a
reader can do it in under a minute.

### 5.3 Coverage of invariants

Of the 36 invariants, 33 have a mutation-backed counterexample. The remaining three are process
invariants that have no code path to break (`INV-ADS-009` architecture revision rather than
patching, `INV-ADS-010` human approval for protected changes, `INV-ADS-011` no test deletion).
They are recorded as declared-but-not-mutation-backed rather than quietly counted as covered,
and the deletion invariant is additionally enforced by a structural check that compares test
module counts across rounds.

---

## 6. Review, QA and CI/CD

### 6.1 Pipeline

`.github/workflows/ci.yml` runs seven jobs on every pull request:

| Job | What it runs |
|---|---|
| Gate 1 · Test approval | `check_test_approval.py` |
| Gate 2 · Static analysis | `ruff check`, `mypy` |
| Gate 3 · Schema | `validate_requirements.py` |
| Gate 4 · Semantic evaluation | `check_semantic_eval.py` (triggers replay on prompt/auction changes) |
| Gate 5 · Regression | full offline suite, 679 tests |
| Gate 5b · Mutation verification | 33 injections, each in a subprocess |
| Gate 6 · AI-use log | `check_ai_use_log.py` |

### 6.2 The gate that never ran

Between 2026-10-11 and 2026-11-05 every CI run finished "successfully" with **zero jobs**. The
cause was a workflow-level `env` entry referencing `${{ runner.temp }}`: the runner context is
not available at that scope, so GitHub rejected the workflow before scheduling any job, and the
UI still showed a completed run.

This is the single most instructive defect of the project. It is not a code bug; it is a
verification bug, and a green badge actively lied to us. The fix moved the expression into the
step that uses it (`8d9a14c`), after which seven jobs registered. We now treat "job count > 0"
as the first thing to check, and the episode is written into the handover as a pitfall.

### 6.3 What the numbers mean

| Measure | Value | What it does **not** prove |
|---|---|---|
| Offline tests | 679 passing | That the system picks good advertisements |
| Mutation injections | 33/33 detected | That every invariant is covered — only the declared ones |
| Fixed evaluation cases | 57 (25 V1 + 18 V2 + 14 V3) | Real-user quality; the model is mocked offline |
| V3 module coverage | 86% | Behaviour on data outside the 5,000-row subset |
| Latency (corpus mode) | ~0.24 s per stage; 0.74 s CLI wall clock | Performance at 25,899 rows |

We state the right-hand column explicitly because an impressive left-hand column is exactly
where projects like this usually start over-claiming.

### 6.4 Independent test execution

A separate test pass was performed by the quality member against the delivered branch, and its
conclusions are committed under `docs/testing/` with the raw evidence under `evidence/v3/`.
It found a real defect we had missed: the corpus manifest recorded SHA-256 hashes computed on
Windows CRLF bytes, so a LF checkout disagreed with the manifest and the integrity test failed.
The root cause was in our generator (it wrote platform-dependent line endings); the fix writes
LF explicitly and the test now normalises before hashing. The same pass found thirteen lint
findings, a non-UTF-8 stdout contract on Windows (now fixed), and confirmed the gate-1 mapping
gaps that we then closed.

### 6.5 Review

Review was structured as a memo with an explicit verdict (`docs/review-memo.md`), not a
comment thread. The V2 memo returned CHANGES REQUIRED on four items before acceptance, and the
V3 review produced the finding list above. Pull requests #2 and #3 are the two integration
points; #3 carried 21 commits and the full evidence package.

---

## 7. Challenges and Rework

### 7.1 Governance built after the first code

The first four commits (2026-09-30) predate the gate system entirely. Tests and implementation
were written together, so the "approved before implementation" property cannot be satisfied for
them by any honest means. We recorded this as `TD-018` / `TD-021` and rebuilt the ordering for
everything that followed.

The lesson is uncomfortable and worth stating plainly: **the artifact that enforces discipline
is the easiest one to postpone**, precisely because postponing it has no visible cost until the
moment you need it.

### 7.2 The blind protocol costs real rework

Test-first with a human approval step slows delivery noticeably; a change that took one turn
now takes three (test, approval, implementation). We kept it because the alternative has a
silent failure mode. The compromise is that trivial refactors may be done without new tests but
must not change a test's assertions — enforced by the approval gate only for changed test files.

### 7.3 Green tests that could not fail

The first mutation run found four counterexample tests that passed even with the implementation
deliberately broken. Two of them asserted a condition that was true for unrelated reasons; two
called a helper directly instead of going through the path under test, so the mutation was
applied to a binding the test never used.

This is the strongest argument in the report for mutation testing. Coverage says which lines
ran; mutation says whether the assertion would notice.

### 7.4 Real data is mostly edge cases

The corpus exposed three properties we did not anticipate:

| Property | Count | Consequence |
|---|---|---|
| Records with empty `content_descriptors` but non-empty `content_warnings` | 8,877 (34%) | A descriptor-only content filter admits a third of the violent material |
| Records with empty `genres` | 34 | Category projection needs a deterministic fallback chain |
| Records with `required_age = 0` | ~97% | Age can never be the primary signal; it is a second-line backstop |

Each of these became a rule in the projection or grading layer, and each is covered by a test
that would fail if the fallback were removed.

### 7.5 Two estimation conventions, three times apart

V1 estimates prompt tokens as `ceil(len/3)`. V2 uses UTF-8 byte length as a conservative proxy.
The second is roughly three times more pessimistic, which means the same 2,000-token budget
holds 30 corpus candidates in V1 but only 4 in V2. We did not hide this: `config-v3.yaml` sets
`top_k: 4` for the V2 corpus mode with a comment explaining why, and the discrepancy is listed
as a limitation rather than a tuning choice. Unifying the two conventions is future work.

### 7.6 The prompt could not be validated offline

Aligning the prompt with the new corpus was straightforward; proving it helped was not. The
offline replay uses a deterministic mock that ignores the prompt entirely, so a prompt change
provably cannot move the offline numbers. We therefore limited the change to factual defects
(scene semantics, no outside knowledge, removing noise) and deferred quality tuning until a
real model and a human-labelled comparison set existed. That set now exists in
`docs/testing/V3-live-prompt-human-labels.json`, and its first result — the model choosing
tag-matching over famous titles 10/10 — is the evidence we were missing.

### 7.7 Where the system is still weak

- **Runtime monitoring is registered but not wired** (`TD-001`). The monitor catalogue exists;
  nothing emits to it.
- **The corpus is a 5,000-row subset** of 25,899, chosen by deterministic stratified sampling.
- **The 5% fee is a demo rule**, not a billing model; there is no reconciliation.
- **V2's candidate ceiling of four** makes the auction thin in corpus mode.
- **Gate 1 is red for the V3 history** and will remain so; the mechanism works going forward.

---

## 8. Conclusion

The project's contribution is not the recommendation engine itself — a five-step gate and a
second-price-less auction are simple mechanisms. The contribution is the arrangement that keeps
them honest: requirements that fail the build when unimplemented, invariants that fail the build
when unfalsifiable, a window of tests that the implementation author is not allowed to read, and
a gate that reports its own historical failure instead of papering over it.

Three years of "AI writes code" projects fail in the same way: the code looks right, the tests
look right, and nobody can tell whether either has ever caught anything. Our answer was to make
that question machine-checkable, and then to publish the places where the answer is still no.

---

## Appendix A — Evidence index

| Claim | Artifact |
|---|---|
| 61 requirements, typed and validated | `docs/req/requirements.yaml`, `docs/req/req-schema.json`, `scripts/validate_requirements.py` |
| 36 invariants with fallbacks | `docs/architecture/invariants.md`, `docs/code-governance/acceptance-coverage-map.yaml` |
| Authority boundaries | `docs/architecture/adr-001-guarded-hybrid.md`, `adr-002-fail-closed-and-governance.md` |
| V2 separation | `docs/architecture/adr-005-*` |
| V3 corpus boundary and pricing | `docs/architecture/adr-006-v3-corpus-boundary.md` (D1–D9) |
| 679 tests, 33 mutations | `test/offline/`, `scripts/mutation_check.py` |
| 57 evaluation cases | `eval/eval_cases.json`, `eval/v2_cases.json`, `eval/v3_cases.json` |
| Independent test evidence | `docs/testing/V3-Test-Report.md`, `evidence/v3/` |
| Human approvals | `docs/test-approvals.yaml` (TA-0001…TA-0007) |
| AI usage | `docs/ai-use-log.yaml` (AIU-0001…AIU-0029) |
| Defects and debt | `docs/bug-diary.md` (BUG-001…008), `docs/debt-register.md` (TD-001…028) |
| Branch protection | `docs/branch-protection.md`, `.github/CODEOWNERS` |
| Operator guide | `docs/HANDOVER-V3.md` |

## Appendix B — Reproduction

```bash
# offline suite (679 tests, ~26 s)
pytest test/offline -q

# gates, in the order CI runs them
python scripts/validate_requirements.py
python scripts/fitness_functions.py
python scripts/check_test_approval.py --base origin/main
python scripts/check_semantic_eval.py --base origin/main
python scripts/check_ai_use_log.py --base origin/main
python scripts/mutation_check.py

# the three round replays
python eval/eval_runner.py
python eval/v2_runner.py
python eval/v3_runner.py

# end-to-end with the real corpus
python -m app --corpus --time-slot night --device mobile --tag student
python -m app.cli_v2 --corpus --request-id r1 --time-slot afternoon --device desktop --tag family
```
