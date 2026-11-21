# V1 Live Prompt Semantic Quality Report

> Status: PASS_WITH_LIMITATIONS
> Human confirmation: CONFIRMED
> Prompt version: `ctx-v1.1`
> Model: `deepseek-flash`
> Provider: OpenAI-compatible HTTP
> Run ID: `v3-20261120-1613818-01`
> Case scope: 6 real scenes × 3 runs

## 1. Result

| Check | Result |
|---|---:|
| Structural validity | 18/18 |
| Ad outcomes | 18/18 |
| No-ad outcomes | 0 |
| Audit provenance | `model_version=openai_compatible/deepseek-flash`, `prompt_version=ctx-v1.1` |
| Real model tested | YES，through the test-only V1 client injection |

## 2. Scene Summary

| Scene | Selected candidates | Proposed label |
|---|---|---|
| family / afternoon / desktop | `ad_316610` ×3 | Family-friendly casual puzzle match |
| student / morning / mobile | `ad_351030` ×3 | Casual/public-setting match |
| gamer / evening / desktop | `ad_2630` ×3 | Competitive/action match |
| family / evening / tablet | `ad_96000` ×3 | Cozy family puzzle match |
| student / night / mobile | `ad_316610` ×2, `ad_351030` ×1 | Cool-down/relaxing match |
| esports / afternoon / desktop | `ad_218230` ×3 | High-intensity multiplayer shooter match |

All selected items are plausible for the given tags. The corrected `esports`
scene now enters the competitive tier and no longer gets blocked as campus.

## 3. Confirmed Human Labels

| Group | Proposed label |
|---|---|
| family scenes | `ACCEPTABLE_FAMILY_MATCH` |
| student scenes | `ACCEPTABLE_STUDENT_MATCH` |
| gamer scene | `ACCEPTABLE_COMPETITIVE_MATCH` |
| esports scene | `ACCEPTABLE_HIGH_INTENSITY_MATCH` |

These labels still require human confirmation.

## 4. Important Boundary

This is a **test-only V1 live path**:

```text
app.pipeline.recommend(client=HTTPSelectorClient)
```

The product V1 CLI still hardcodes `MockLLM`. Therefore this proves that the
V1 prompt/parser/pipeline can work with a real model under test injection, but
it does not mean the product V1 default runtime is live.

## 5. Evidence

Raw results:

`evidence/v3/v3-20261120-1613818-01/16-v1-live-prompt/v1-live-semantic-results.json`

The append-only audit file contains smoke and formal runs; use
`filter_v1_live_audit.py` to extract the final 18 records before packaging.

Filtered final audit evidence:

`outputs/v1-live-final.audit.jsonl`（当前工作区；18 条）

## 6. Final Status

```text
V1 Live Structural Validity: PASS
V1 Live Semantic Quality: PASS_WITH_LIMITATIONS
V1 Product Live Path: NOT APPLICABLE（product CLI uses MockLLM）
Human Confirmation: CONFIRMED
```
