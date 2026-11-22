# V3 Final Evidence Package

> Run ID: `v3-20261120-1613818-01`
> Tested code commit: `161381887e421a121cd2878fcbf397d42a8ac818`
> Evidence status: COMPLETE
> Overall result: PASS_WITH_LIMITATIONS
> Course delivery readiness: CHANGES REQUIRED

## Purpose

This directory packages the final V3 test, live semantic, and screenshot acceptance evidence. The deterministic product evidence and live-model evidence are kept separate so that live results are not treated as replacements for offline regression.

## Related Runs

| Run ID | Scope |
|---|---|
| `v3-20261120-53d37fc-01` | environment, source, collection, initial data diagnostics |
| `v3-20261120-15cc289-01` | V3 core tests and post-manifest-fix full regression |
| `v3-20261120-4d0479f-01` | V1/V2 E2E, replay, mutation, intermediate static checks |
| `v3-20261120-1613818-01` | post-Ruff regression, governance, final static checks, coverage, live probes, screenshot demo |

The current directory is the `1613818` final acceptance run. Earlier run directories remain as traceable history.

## Final Result

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

## Main Evidence

| Path | Content |
|---|---|
| `12-post-ruff/` | post-Ruff full regression and mutation |
| `13-governance/` | AI-use log, semantic eval, test approval |
| `14-final-static/` | eight final static checks |
| `15-coverage/` | coverage XML and terminal summary |
| `16-live-prompt/` | V2 `relevance-v2.2` live semantic evidence |
| `16-v1-live-prompt/` | V1 `ctx-v1.1` test-only live semantic evidence |
| `17-final-demo/` | 10 final screenshots and reproducible command scripts |

## Integrity

Verify all packaged files from this directory:

```powershell
$bad = Get-Content .\checksums.sha256 | ForEach-Object {
    $hash, $path = $_ -split '\s{2}', 2
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLower() -ne $hash) { $path }
}
if ($bad) { $bad } else { 'CHECKSUMS_OK' }
```

## Limitations

- Gate 1 remains `DEFERRED / FAIL` because requirement-to-test/evidence mappings and human approval are incomplete.
- V1 product CLI remains `Mock / Offline`; the V1 live result is test-only.
- Live semantic labels cover six controlled scenes and are not a broad human-labeled corpus.
- Coverage is recorded at 86% without a mandatory project threshold.
- Course delivery is not ready until the governance blocker is resolved.
