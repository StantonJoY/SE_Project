# CS5351 V3 Screenshot Demo Script

## 1. Demo Information

| Item | Value |
|---|---|
| Version | V3 final acceptance |
| Tested code commit | `161381887e421a121cd2878fcbf397d42a8ac818` |
| Docs/evidence commit | `4da29339ae7e150302fe7123422bf78fa8135c04` |
| Run ID | `v3-20261120-1613818-01` |
| Environment | Conda `SEProjectV3` / Python 3.11.18 |
| Demo style | Terminal screenshots + reproducible command scripts |
| Status | SCREENSHOT_CAPTURE_COMPLETE（10/10）/ EVIDENCE_COMPLETE |

## 2. Scope

Covered:

- 5,000 Steam corpus and manifest integrity;
- V1 corpus recommendation and invalid scene;
- family/campus/competitive safety rules;
- V2 pricing, auction, idempotency, conflict and budget;
- full regression, replay and mutation;
- static checks and coverage;
- V1/V2 live semantic evidence;
- Gate 1 limitations.

Not claimed:

- product V1 live path (V1 product CLI remains Mock/Offline);
- broad human-labeled live semantic corpus;
- Gate 1 passing.

## 3. Screenshot List

Save under:

```text
evidence/v3/v3-20261120-1613818-01/17-final-demo/screenshots/
```

| # | File | Content |
|---|---|---|
| 01 | `01-environment.png` | branch, tested code commit, docs commit, Conda, editable path |
| 02 | `02-corpus.png` | 5,000 rows, manifest hash match, 34 empty genres / 715 age-gated |
| 03 | `03-v1-normal.png` | V1 corpus normal result, 30 candidates, audit=1 |
| 04 | `04-v1-invalid.png` | illegal `day` scene, `scene_invalid`, audit=1 |
| 05 | `05-content-safety.png` | content tier and age-gate tests |
| 06 | `06-v2-auction-budget.png` | V2 auction, idempotency, conflict, budget |
| 07 | `07-regression-replay-mutation.png` | 675 tests, V1/V2/V3 replay, mutation 33/33 |
| 08 | `08-static-coverage.png` | static checks PASS and 86% coverage |
| 09 | `09-live-prompt.png` | V2 30/30 and V1 test-only 18/18 semantic results |
| 10 | `10-gates-limitations.png` | Gate 1 DEFERRED/FAIL and final readiness |

## 4. Commands

Run from the V3 worktree:

```powershell
Set-Location 'E:\cityu\SE\project\SE_Project-v3-test'

$Demo = 'E:\cityu\SE\project\SE_Project-v3-test\evidence\v3\v3-20261120-1613818-01\17-final-demo'

& "$Demo\commands\01-baseline.ps1"
& "$Demo\commands\02-corpus.ps1"
& "$Demo\commands\03-v1-demo.ps1"
& "$Demo\commands\04-v2-demo.ps1"
& "$Demo\commands\05-tests-replay.ps1"
& "$Demo\commands\06-live-prompt.ps1"
& "$Demo\commands\07-limitations.ps1"
& "$Demo\commands\08-content-safety.ps1"
& "$Demo\commands\09-static-coverage.ps1"
```

`03-v1-demo.ps1` produces both normal and invalid output. Capture the normal portion as `03` and the invalid portion as `04`.

## 5. Screenshot Rules

- Each screenshot must contain a section title and key result.
- Do not display API keys, Authorization headers or sensitive endpoints.
- Mark V1 as `Mock / Offline`.
- Mark V1 live as `test-only`.
- Mark Gate 1 as `DEFERRED / FAIL`.
- Do not write `Course Delivery: PASS`.

## 6. Final Status

```text
V3 Functional Testing: PASS
V3 Full Regression: PASS（675）
V3 Replay: PASS
V3 Mutation: PASS（33/33）
V3 Static Checks: PASS
V3 Coverage: RECORDED（86%）
V2 Live Prompt: PASS_WITH_LIMITATIONS
V1 Live Prompt (test-only): PASS_WITH_LIMITATIONS
V1 Product Default Path: Mock / Offline
V3 Screenshot Demo: COMPLETE（10/10）
V3 Evidence Package: COMPLETE
V3 Governance: DEFERRED / FAIL
V3 Course Delivery Readiness: CHANGES REQUIRED
```
