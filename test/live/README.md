# V3 Live Test Tools

These scripts exercise real model providers and are intentionally separate from
the deterministic offline test suite.

## Files

| File | Purpose |
|---|---|
| `run_v1_live_semantic.py` | Test-only V1 `ctx-v1.1` LLM client injected through `app.pipeline.recommend` |
| `run_v2_relevance_live.py` | V2 `relevance-v2.2` multi-scene semantic probe using `HTTPRelevanceClient` |
| `filter_v1_live_audit.py` | Extract the final 18 V1 live audit records from the append-only audit file |

## Environment

Use environment variables; never write credentials into a file:

```powershell
$env:V3_LIVE_ENDPOINT = 'complete chat-completions URL'
$env:V3_LIVE_MODEL = 'deepseek-flash'
$env:V2_LLM_API_KEY = 'provider API key'
```

## Run

From the V3 repository root:

```powershell
python test/live/run_v1_live_semantic.py --runs-per-scene 3
python test/live/run_v2_relevance_live.py --runs-per-scene 5
```

## Outputs

- `run_v1_live_semantic.py` writes `v1-live-semantic-results.json` and
  `v1-live.audit.jsonl` under `16-v1-live-prompt/`.
- `run_v2_relevance_live.py` writes
  `live-prompt-multi-scene-results.json` under `16-live-prompt/`.
- The V2 script also writes a single-scene baseline for backward comparison
  when explicitly requested through `--output`.

## Boundaries

- V1 product CLI remains `Mock/Offline`; the V1 script is a test-only harness.
- V2 `relevance-v2.2` uses the real HTTP provider when configured.
- Live semantic labels require human confirmation.
- Gate 1 test approval is independent of this directory.
