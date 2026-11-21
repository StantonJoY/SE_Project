# V3 Live Prompt Semantic Quality Report

> Status: PASS_WITH_LIMITATIONS
> Human confirmation: CONFIRMED
> Run ID: `v3-20261120-1613818-01`
> Prompt version: `relevance-v2.2`
> Provider: HTTP real model
> Case scope: 6 real scenes × 5 runs, 5 title-bait cases, 5 known-title cases

## 1. Result

| Check | Result | Interpretation |
|---|---|---|
| Real HTTP call | PASS | Real provider path was used |
| Prompt version | `relevance-v2.2` | V3 relevance prompt |
| Multi-scene structural validity | 30/30 | Every response across six scenes parsed under the strict schema |
| Multi-scene selected distribution | See Multi-Scene Expansion below | All selected candidates were tag-consistent for their scenes |
| Title-bait cases | 5/5 selected the tag-matching candidate | Title wording did not override target tags |
| Known-title cases | 5/5 selected the tag-matching candidate | Famous titles did not override family/tag fit |

## 2. Confirmed Human Labels

The current human reviewer accepted these labels for the documented run and scope.

| Group | Confirmed label | Basis |
|---|---|---|
| Repeated family scene | `ACCEPTABLE_FAMILY_MATCH` | All selected candidates have family-friendly/tag-compatible signals |
| Title bait | `PASS`, 5/5 | The model selected `match_*` and gave low relevance to bait items |
| Known title | `PASS`, 5/5 | The model selected the lower-fame, tag-matching candidate |

## 3. Important Boundaries

- This is one real-model sample, not a broad human-labeled benchmark.
- The artificial title-bait and known-title cases use synthetic candidate summaries.
- V1 is offline-only by design; V1 live prompt testing is `NOT APPLICABLE`, not a missing V3 test.
- The labels were confirmed by the current human reviewer; the named reviewer should be filled in the matching JSON.
- It does not replace the fixed offline replay or the full regression suite.

## 4. Multi-Scene Expansion

The expanded harness ran 6 scenes x 5 calls:

| Scene | Structural | Selected distribution | Confirmed label |
|---|---:|---|---|
| family / afternoon / desktop | 5/5 | `ad_2993780` 5 | Family-friendly and relaxing |
| student / morning / mobile | 5/5 | `ad_351030` 5 | Casual/puzzle, appropriate |
| gamer / evening / desktop | 5/5 | `ad_6030` 4, `ad_10180` 1 | Action/shooter, appropriate |
| family / evening / tablet | 5/5 | `ad_259550` 4, `ad_346560` 1 | Cozy/relaxing family-friendly |
| student / night / mobile | 5/5 | `ad_351030` 4, `ad_348620` 1 | Cozy/relaxing, appropriate |
| competitive / afternoon / desktop | 5/5 | `ad_385770` 5 | Competitive tag present; content specificity is limited |

Multi-scene structural validity: `30/30`.

Title bait: `5/5` selected the tag-matching candidate.

Known-title comparison: `5/5` selected the tag-matching candidate.

Confirmed multi-scene semantic label:

```text
PASS_WITH_LIMITATIONS
```

This is stronger than the single-scene result because it covers different
time/device/tag combinations. It still does not cover all scenes or a broad
human-labeled Steam corpus.

## 5. Limitations

- Only `deepseek-flash` over one HTTP provider was tested.
- The real-scene sample is `6 scenes × 5 runs`, not a broad statistical sample.
- Title-bait and known-title cases use synthetic candidate summaries, not a broad human-labeled Steam corpus.
- `competitive_afternoon` is tag-consistent, but the selected idle game has weaker competitive content specificity.
- V1 `ctx-v1.1` live semantic quality is not applicable because V1 is intentionally Mock/Offline.
- The direct relevance-client harness does not by itself prove live pipeline audit provenance persistence.
- This result does not replace fixed offline replay, compliance tests, full regression, or broad human-labeled live quality.
- Gate 1 test approval remains `DEFERRED / FAIL`.

## 6. Evidence

Raw results:

`evidence/v3/v3-20261120-1613818-01/16-live-prompt/live-prompt-multi-scene-results.json`

Single-scene baseline:

`evidence/v3/v3-20261120-1613818-01/16-live-prompt/live-prompt-results.json`

## 7. Final Status

```text
Live Prompt Structural Validity: PASS
Live Prompt Semantic Quality: PASS_WITH_LIMITATIONS
Human Confirmation: CONFIRMED
V1 Live Prompt Coverage: NOT APPLICABLE（V1 offline-only）
```
