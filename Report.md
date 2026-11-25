# Scenario-Based Ad Recommendation Engine

## Team Delivery Report — Rounds V1 to V3

| | |
|---|---|
| Repository | `github.com/StantonJoY/SE_Project` |
| Delivered commit | `8b5a17a` (merge of PR #3, `v3` → `main`), plus `a9c79d8` (branch-protection preparation) |
| Report version | 1.0 — 2026-11-22 |
| Team | Shen Jiyun (60989886), Gong Yuebin (60652349), Zhang Qiyan (60805659), Gao Zhechun (student ID pending) |
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

### 1.4 Open questions: four closed, five decided in practice, one waiting on a person

Ten open questions were opened (`OQ-001`…`OQ-010`). Four carry an explicit `status: closed`
in the registry; five were decided in practice and are recorded in the ADR they produced; one
is still open because it depends on human acceptance, not on the team. We report the split
rather than claiming all ten are closed:

| State | Questions | Where the decision lives |
|---|---|---|
| Closed in the registry | `OQ-004` (confidence threshold), `OQ-005` (evaluation-set scope), `OQ-009` (definition of "explanation"), `OQ-010` (sandbox `tmp_path` limitation) | `requirements.yaml` `open_questions[].status` |
| Decided in practice, status field not yet flipped | `OQ-001` (model provider), `OQ-002` (banned-word list scope), `OQ-003` (ad-material size), `OQ-006` (pay-as-bid vs. Vickrey), `OQ-007` (score formula) | ADR-001 (provider boundary), ADR-005 (`pay-as-bid`, `relevance × bid`), `data/` contents |
| Still open | `OQ-008` (formal human acceptance of the V2 round) | `docs/v2-approval-status.yaml` |

Two that shaped the delivery: **OQ-005** fixed the evaluation-set size ("at least 20 cases per
round, negatives counted separately"), and **OQ-009** fixed that an explanation must state
*why this one* — which is why the explanation path is structurally isolated from the decision
path (ADR-001).

### 1.5 Requirement types, priorities, and what the numbers mean

The registry is typed, and the type is not cosmetic: it decides which fields are mandatory.
The distribution is deliberately skewed toward invariants, because in a system whose AI
component must be constrained by deterministic code, the non-negotiable rules *are* the design.

| Type | Count | Mandatory extra field | Why it exists |
|---|---|---|---|
| Invariant | 26 | `fallback` (concrete action when violated) | Forces fail-closed thinking instead of "detect and log" |
| Functional | 14 | `enforcement` (the symbol that implements it) | Prevents documented-but-unimplemented requirements |
| Quality | 8 | `metric {name, unit, threshold, direction}` | Makes "good enough" checkable |
| Governance | 6 | `enforcement` | Keeps the process artifacts themselves verifiable |
| Security | 3 | `enforcement` | Injection surface and credential boundary |
| Performance | 2 | `metric` | Latency budget for corpus mode |
| Cost | 2 | `metric` | Prompt-token ceiling per request |

Priority uses MoSCoW: **58 must**, **3 should**, zero could/won't. Rather than leave the
tradeoff implicit, `docs/req/requirements.yaml` now carries a `prioritization` block listing four
concrete tradeoffs (ADR-007), each tied to the requirement IDs it affects.

### 1.6 What "done" means

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

### 2.7 The V2 settlement path, step by step

V2 is where the authority chain is easiest to get wrong, so the data flow is written out
explicitly. Each step names the artifact that owns it.

| # | Step | Owner | What travels | Failure behaviour |
|---|---|---|---|---|
| 1 | Load bids sidecar | `bidding.validate_bids` | `ad_id`, `bid_cents`, `budget_cents`, `status` | Malformed or out-of-range bid → whole sidecar rejected, request fails loudly |
| 2 | Pre-select candidates | `AdRepository.filter_by_scene` (+ V3 `candidate_ids`) | `Ad` objects | Empty set → `no_ad / no_candidates` |
| 3 | Ask for relevance | `selector.relevance` client | `scene` + candidate summaries | Timeout/parse error → `no_ad` (`RP-004`), never a guess |
| 4 | Verify affordability | `bidding.ledger.budgets()` | Remaining budget per `ad_id` | Inactive or unaffordable bids are removed before the auction |
| 5 | Choose winner | `bidding.engine.choose_winner` | `relevance × bid`, ties by ascending `ad_id` | No positive score → `no_ad / no_relevant_candidates` |
| 6 | **Compliance gate** | `compliance.run_compliance` (FINAL AUTHORITY) | The winning `Ad` | Rejected → `no_ad / compliance_rejected`, **nothing is charged** |
| 7 | Settle | `bidding.ledger.finalize` | charge, result, evidence | One SQLite transaction; any fault → full rollback, `status_unknown` |
| 8 | Render + audit | `render.schema_v2` / ledger audit row | `ad` + `auction` block | Schema-invalid result → `no_ad`, never a partial output |

Two properties are worth stating because they are the reason for the ordering:

- **Money is computed before compliance but committed after it.** Step 6 can still reject the
  winner; step 7 only runs on approval. The ledger therefore never records a charge for an ad
  that compliance refused.
- **Repetition is free, divergence is not.** `request_id` is the idempotency key: the same id
  with the same inputs returns the stored response without a second charge, while the same id
  with different inputs returns `request_conflict` and charges nothing. Both behaviours are
  covered by tests, not by convention.

---

## 3. Team Organization and Contributions

### 3.1 Roles

| Member | Role | Primary scope |
|---|---|---|
| Shen Jiyun (60989886) | PM / architecture / AI | Theme and iteration direction, process-artifact system, V1 and V3 implementation |
| Gong Yuebin (60652349) | Architecture / AI review | Requirements and ADR review, prompt and model decisions |
| Zhang Qiyan (60805659) | Application / integration | V2 auction and ledger integration, CLIs |
| Gao Zhechun (student ID pending) | Quality / governance | Independent test execution, evidence packaging, gate verification |

### 3.2 Relative contribution

The course asks for a relative-contribution table whose **average is 1.0**. We report both the
share and the derived factor, because a factor alone forces the reader to reverse-engineer it:

| Member | Share | Relative factor | Note |
|---|---|---|---|
| Shen Jiyun (60989886) | 31.25% (5/16) | **1.25** | PM; theme and iteration direction; process-artifact system; V1 and V3 implementation |
| Gong Yuebin (60652349) | 22.92% (11/48) | **0.917** | Architecture / AI review |
| Zhang Qiyan (60805659) | 22.92% (11/48) | **0.917** | Application / integration |
| Gao Zhechun (student ID pending) | 22.92% (11/48) | **0.917** | Quality / governance |
| **Average** | **100%** | **1.000** | (1.25 + 0.917 × 3) / 4 = 1.0 |

The shares are exact fractions: 5/16 for the first member and 11/48 for each of the other
three (11/48 × 3 + 5/16 = 1). The decimals shown are rounded for readability; the factors are
derived from the fractions, not from the rounded percentages.

*Factor = share × 4. The four members must agree on the shares before submission; the
placeholder row values are not filled in by an agent.*

### 3.3 Self-evaluations

> **Note to the reader:** the course requires each member's self-evaluation to be written by
> that member. The paragraph below was drafted from the repository record by Shen Jiyun's
> assistant and is to be restated in his own words before submission.

#### Shen Jiyun (60989886) — self-evaluation

I was the team's PM, and my work fell into three buckets: direction, system, and code.

**Direction.** From round one I fixed the project's thesis: the AI is an advisor and the code
is the executive. The model may only choose inside a closed candidate set, and whether anything
is displayed is decided by a deterministic compliance pipeline. That single boundary kept the
later rounds honest — the V2 auction and the V3 corpus integration both had obvious ways to
bypass the gate, and both were rejected on the same grounds.

**System.** I built the process artifacts that make the claims checkable: a 61-entry
requirement registry, 36 invariants with explicit fallbacks, ADRs for every protected path, a
trace matrix, seven CI gates (six checks plus mutation verification), an AI-use log, and named human test
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

#### Gong Yuebin (60652349) — self-evaluation

I formed the team, bringing three other students together when the assignment allowed us to
choose our own groups.

Before any code existed, I settled what the project had to hand in. I went through the course
specification and turned it into the team's working shape: which artifacts were required, how the
repository would be laid out to hold them, and how each round of work would be logged. That held
for the rest of the project.

The round I led myself was V3, and it was defined before anything was built. V1 and V2 were done
and nothing had been written down for V3, so its scope was mine to set. Three calls shaped it.
First, scope: the agent started by proposing retrieval, embeddings and a vector store, and I cut
that, since ranking by similarity is another course's problem and our compliance chain is a hard
filter that a score cannot feed into. Second, structure: I set the split into must-do,
recommended and optional, and every later item had a place to go. Third, evidence: I asked
whether the agent had actually read the corpus it was writing requirements against. It had looked
at the field definitions and one sample row. I handed over thirty real records, and that is when
the draft's projection rule broke on records with an empty genre list, and when a severity field
that reads zero on most violent titles turned out to be useless as an age filter. Both
corrections made it into the final requirements. My two drafts are cited in the repository as the
source of the V3 requirements, and their fifteen entries map onto the nineteen that were
registered.

The rest of my work was catching the project up on itself. Gate 5 had been failing on every pull
request on a module that could not be imported, and my own diagnosis of it was wrong until two
pull requests opened in the same hour, one green and one red, disagreed with me. I also fixed the
README's counts, gave all twenty-eight debt entries a status, and wrote four architecture
documents the course asks for that the repository did not have.


#### Zhang Qiyan (60805659) — self-evaluation

I was responsible for iterating on and extending V2. Building on V1, I used Codex agents to develop a deterministic, single-winner advertising auction and persistent budget management. The model provided relevance scores, while the code ranked candidates using relevance multiplied by bid, resolved ties by advertisement ID, and charged the winner its own bid. Compliance checks retained the final authority to reject an advertisement before charging. SQLite ensured that budget updates, request results, and audit records were committed together, while request replay prevented duplicate charges. I also used the agents to check the implementation against the course specification and V2 handover document, run regression tests and fixed-case evaluations, organize verification materials, and prepare the GitHub submission. A subsequent CI configuration fix enabled GitHub Actions to run the checks. The missing evidence of pre-implementation human test approval remained documented as a process limitation.

This group assignment differed from those in other courses and offered a fresh approach to project work. However, as AI becomes more capable, I feel that users’ interventions have a diminishing influence on the results of relatively straightforward tasks. During my V2 work, I tried different prompts and found little difference in the outputs. Nevertheless, I deliberately adopted more detailed conversational prompts partly to improve the presentation and make the amount of work involved more visible. This made me question how effectively the length or detail of a conversation demonstrates a student’s contribution. I considered using a weaker agent or model, but then wondered why I should choose an older, less capable tool when a better one was available simply to demonstrate my own ability. To me, that would be like applying an outdated standard after the circumstances had changed. My greatest gain from this project was the thinking that took place while using AI. Following the implementation, asking questions about its behavior, and examining the verification results helped me understand the project’s components and how they worked together.

#### Gao Zhechun (student ID pending) — self-evaluation

My main contribution was independent quality assurance across the whole project, not only the final V3 round. I treated each delivered version as a separate test target and verified that it could be reproduced outside the original development workspace. For V1, I created an isolated test directory, confirmed the Conda environment and editable package path, and ran the deterministic offline tests, fixed evaluation replay, CLI scenarios, and evidence collection. I also checked the audit output and the fail-closed behaviour for invalid scenes. The V1 work established the testing pattern I reused later: verify the environment first, preserve the command output, record the exit code, and keep the evidence traceable.

For V2, I used a separate worktree and Conda environment so the V1 baseline and evidence would not be overwritten. I tested the auction and settlement path, request idempotency, budget persistence, request conflicts, and regression against V1. I also supported the real-model path and recorded where Live testing differed from fixed offline behaviour. The screenshot demonstration, command scripts, manifest, and checksums were built so the reviewer could reproduce both the functional result and the limitations. This round made it clear that passing tests alone was not enough; the accounting, audit, and deployment boundaries also had to be checked.

For V3, I verified the final corpus, investigated the manifest hash mismatch, confirmed the final JSONL data with the team, and checked content grading, age gating, V1/V2 integration, replay, mutation, static analysis, coverage, and live semantic evidence. The V3 work was important, but it was the same independent verification process applied to a larger and more safety-sensitive data set.

Across all three rounds, I organized the execution records, raw logs, screenshots, checksums, and session transcripts. I kept unresolved issues visible. I did not own most product implementation, but I provided the external check on whether the delivered system, evidence, and claims matched each other.

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
| Corrupted identifiers | First V3 draft used an ID prefix the validator rejects | `scripts/validate_requirements.py` |

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
| `scripts/validate_requirements.py` | Unknown ID, duplicate, missing fallback, enforcement pointing at nothing |
| `scripts/fitness_functions.py` | Element/module drift (S1), deletion of an element (S2), missing ADR references (S3), missing round criteria (V1–V4) |
| `check_safety_paths.py` | A protected path changed without an accompanying ADR |
| `scripts/check_test_approval.py` | Tests changed without a prior named human approval |
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

### 5.4 What mutation testing changed

Coverage told us which lines ran. Mutation told us whether the assertions would notice if the
line were wrong — and the first run found four "counterexamples" that passed even with the
implementation deliberately broken. Three representative entries from the final set of 33:

| Mutation | What it breaks | Test that must fail | Verdict when injected |
|---|---|---|---|
| `MUT-V3-BID-TEN-PERCENT` | Derives bids at 10% instead of 5% | `test_bid_is_five_percent_of_price` | Fails with `assert 50 != 75` |
| `MUT-V3-LABELS-NO-WARNINGS` | Content grading reads only `descriptors` | `test_among_us_rejected_by_warnings_side` | Fails (the record has empty descriptors) |
| `MUT-V3-SEED-UNBOUNDED` | Seeds 100× budget | `test_twenty_impressions_exhaust_budget` | Fails with `assert 1980 == 0` |

The injections never touch the working tree: they are applied to module attributes in a
subprocess, and the harness only accepts a **genuine assertion failure** — an import error or a
fixture crash does not count as a kill. That distinction matters; without it, injecting an
`ImportError` would "prove" every test suite is effective.

One entry was retired during V3 for being untestable by construction: `INV-ADS-009` requires
revising the architecture rather than patching code, which has no code path to break. It is
recorded as declared-but-not-mutation-backed rather than quietly counted as covered.

---

## 6. Review, QA and CI/CD

### 6.1 Pipeline

`.github/workflows/ci.yml` runs seven jobs on every pull request:

| Job | What it runs |
|---|---|
| Gate 1 · Test approval | `scripts/check_test_approval.py` |
| Gate 2 · Static analysis | `ruff check`, `mypy` |
| Gate 3 · Schema | `scripts/validate_requirements.py` |
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

### 6.6 What the system actually did (measured, not estimated)

All numbers below are from runs on the delivered commit; each is reproducible with the command
noted in Appendix B.

**Content grading across scene tiers** (same time slot `afternoon`, same device `desktop`,
30 candidates per tier — the tiers select different candidate sets, so pass counts are not
directly comparable across rows):

| Tier | Candidates | Passed compliance | Rejected | Dominant rejection reason |
|---|---|---|---|---|
| `family` | 30 | 21 | 9 | `Violence` present in `content_warnings` |
| `campus` (student) | 30 | 10 | 20 | `Violence` (campus blocks it, family's candidate set simply contains fewer) |
| `competitive` (gamer) | 30 | 24 | 6 | `Gore`, `Nudity`, `Sexual Content` |

The `campus` row is the one that justifies the union rule: a descriptor-only filter admits
records whose `content_descriptors` is empty but whose `content_warnings` lists violence.

**Corpus-mode latency** (5,000 rows, single process):

| Stage | Time |
|---|---|
| Config load | ~5 ms |
| Corpus load (2.1 MB + 3.4 MB JSONL) | 234–292 ms |
| Deterministic top-K selection | ~40 ms |
| Projection to `Ad` (30 items) | <1 ms |
| Compliance (30 candidates) | 2–3 ms |
| V1 CLI end-to-end (including interpreter start) | ~0.74 s |

**Budget drain under repeated auction** (V2, one ledger, 300-cent bid = 5% of $59.99):

| Request | Budget before | Budget after |
|---|---|---|
| `req-1` | 6000 | 5700 |
| `req-2` | 5700 | 5400 |
| `req-3` | 5400 | 5100 |

Twenty impressions exhaust the budget exactly; the 21st is refused with `InsufficientBudget`
and produces no charge. Requests 1–3 above are the first three of that sequence.

**Fixed evaluation replays**: V1 25 cases, V2 18, V3 14 — pass rate 1.0000 in all three, zero
violations (compliance escapes, out-of-set selections, audit-count errors, schema errors,
explanation-isolation violations). p95 latency for the V3 partition is under 5 ms because it
uses the deterministic mock client.

---

### 6.7 Branch protection: what we configured and what we measured

Static configuration is not evidence. Protection was verified by running the same command
(direct push to `main`, same account) before and after each change:

| Stage | Configuration | Direct push to `main` |
|---|---|---|
| Before | no rule on `main` | succeeded (`66b1ab4..c6bda63`) |
| After enabling the rule | 6 required status checks, no bypass | **rejected**: `push declined due to repository rule violations`, `6 of 6 required status checks are expected` |
| After adding the owner to the bypass list | rule unchanged, owner exempt | succeeded again (`52717b6..20d5856`) |

The final configuration separates "code must be reviewed" from "docs must not be blocked":

| Setting | Value | Consequence |
|---|---|---|
| Require a pull request | on | no direct pushes by non-owners |
| Required approvals | **0** | any PR can merge once checks pass |
| Require review from Code Owners | on | only paths listed in `.github/CODEOWNERS` require an approval |
| `CODEOWNERS` coverage | `src/`, `data/`, `scripts/`, `eval/`, `test/`, `.github/`, `AGENTS.md`, blueprint | `docs/` is deliberately **unlisted** |
| Required checks | Gate 2, 3, 4, 5, 5b, 6 | Gate 1 excluded while the historical gap is open |
| Bypass list | repository owner | the owner can still push docs directly |

The tradeoff is stated rather than hidden: because the owner is on the bypass list, the rule
constrains *other* accounts but not the owner. Machine enforcement of "code must be reviewed"
therefore applies to everyone except the account that built the system — which is honest for a
four-person course project and would not be acceptable in production. The measurement
(the three-row table above) is kept in `docs/branch-protection.md` §9 so that the claim can be
re-checked instead of trusted.

**Figures.** Three screenshots carry the visual evidence, all from the delivered repository:

- `1.png` — the pull-request list: **16 closed** PRs and **2 open** ones, both open PRs showing
  `6/7` checks with a red mark, i.e. a PR cannot reach "mergeable" while one gate is red;
- `2.png` — the ruleset page for `main`: enforcement **Active**, target **Default**, and the
  bypass list containing **Repository admin** (the reason the owner can still push, disclosed in
  the previous paragraph);
- `3.png` — one PR's checks popover: **6 successful, 1 failing**, the failure being
  `Gate 5 · Regression` after 26 s, while `Gate 1 · Test approval` passes in 12 s. That single
  image shows three things at once: seven gates run as seven separate jobs (12–26 s each), a red
  gate blocks the merge, and a documentation-only change set passes the approval gate without
  needing an approval.

They live in `evidence/v3/v3-20261125-github-gates/{1,2,3}.png`; what each one supports is
itemised in `docs/testing/V3-GitHub-Gate-Evidence.md`.

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

### 7.8 Process quality evidence: volatility, defects, ambiguity

The course asks for evidence that the *process* was managed, not only that the product works.
Three measures, all with data in the repository.

**Requirement volatility.** 61 requirements were added across three rounds and **none were
deleted**; superseded identifiers are preserved in `legacy_id_map` so the history stays
auditable.

| Round | Added | Deleted | Note |
|---|---|---|---|
| V1 | 22 | 0 | Seven architectural elements, closed set of 14 ads |
| V2 | 19 | 0 | Auction + atomic ledger; V1 requirements untouched |
| V3 | 20 | 0 | Corpus, content grading, pricing; V1/V2 requirements untouched |

Volatility appears as **rejected scope**, not as churn: two RAG-direction requirements were
drafted and then withdrawn (`docs/req/requirements-v3-rag-draft.md` is kept as the negative
record), and four tradeoffs are now explicit in `docs/req/requirements.yaml` (§1.4 and ADR-007).

**Defect trends.** Eight significant defects were recorded. Each one is mapped to the
invariant gap it exposed and to the check that now covers it — this is why the checks exist,
not a list assembled afterwards:

| Defect | Area | Invariant gap exposed | Check added |
|---|---|---|---|
| `BUG-001` | tests | Test depended on host temp directory | I/O boundary stubbing rule |
| `BUG-002` | registry | Schema conditional made `asr_id` globally required | Validator rejects orphan ASRs |
| `BUG-003` | registry | A requirement can enforce several ASRs | Bidirectional consistency check |
| `BUG-004` | registry | YAML `>` parsed as folded scalar | Coverage map is parsed by the validator |
| `BUG-005` | tests | Hard-coded material count coupled tests to data | Count derived from the loader |
| `BUG-006` | compliance | Banned-word hit depended on file order | Longest-match + codepoint tie-break, permutation test |
| `BUG-007` | compliance | Loader fail-closed posture differed by module | Uniform fail-closed contract (`TD-014`) |
| `BUG-008` | packaging | `src/audit/` never entered the repository (gitignore `audit/`) | `check_repo_completeness.py` |

The trend across rounds is the interesting part: V1 defects were **test and registry**
defects; V2/V3 defects shifted to **packaging and evidence** defects (CI running zero jobs,
CRLF-hashed manifest, untracked documents). That shift is what the gate set grew to cover.

**Ambiguity.** Ten open questions were opened during requirements work. Four were closed
explicitly, five were resolved by the ADR they produced, and one (`OQ-008`, formal human
acceptance of V2) remains open because it needs a person, not a decision. The registry keeps
closed questions instead of deleting them, so the decision history stays readable.

---

### 7.9 How the process itself was optimised

The course asks not only what process we used but how we improved it. Three changes were made
in response to evidence, not in response to a plan:

| Trigger (evidence) | Change to the process | Rounds affected |
|---|---|---|
| A designer could not state which requirement a module implemented | Requirements became typed, and `enforcement` became a mandatory pointer to a real symbol; the validator rejects a pointer to nothing | V1 → V2 |
| Four "counterexamples" passed under deliberate breakage | Mutation verification became a blocking gate; every declared invariant must have an injection that kills its test | V1 → V2 |
| CI reported success seven times while running zero jobs | "Job count > 0" became the first thing checked on any CI investigation; the workflow-level `env` mistake was written into the handover as a pitfall | V2 |
| The same rule was written in three places and drifted (`16` vs `36` invariants) | Data files and counts are derived from a single source; a documentation-consistency audit now has a recorded procedure | V3 |
| Tests and implementation were written in the same session | Test-first with a named human approval (`TA-*`), enforced by a gate whose timing layer compares approval time with the earliest implementation commit | V3 (forward only) |
| The owner could not push a doc fix without a PR | Branch protection was split: required checks for everyone, Code Owner approval only for code paths, `docs/` deliberately unlisted | V3 |

Two of these are worth naming as **process optimisations that cost something**: mutation
verification adds roughly 50 seconds to every run, and the approval gate turns a one-step
change into three (test → approval → implementation). We kept both because their failure mode
is silent: a green suite that proves nothing, and a merge record that attests to an approval
that never happened.

The pattern across all six rows is the same: **the artefact that enforces discipline is the
easiest one to postpone**, because postponing it has no visible cost until the moment it is
needed. Each change above was made after that moment had already passed once.

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
| Authority boundaries | `docs/architecture/adr-001-guarded-hybrid.md`, `docs/architecture/adr-002-fail-closed-and-governance.md` |
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
