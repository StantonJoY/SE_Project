$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
$r = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'live-p95-results.json') | ConvertFrom-Json
Clear-Host
Write-Host '=== V2 DEMO 10: LIVE PERFORMANCE AND COST ==='
[pscustomobject]@{
    Provider=$r.provider
    EndpointPath=$r.endpoint_path
    Samples=$r.sample_count
    FunctionalSuccessRate=$r.functional_success_rate
    StructuralSuccess=$r.structural_success_count
    SchemaFailures=$r.schema_failure_count
    UsageSuccess=$r.usage_success_count
    P50Sec=$r.p50_sec
    P95Sec=$r.p95_sec
    MaxSec=$r.max_sec
    P95Pass=$r.p95_pass
    CacheHitTokens=$r.prompt_cache_hit_tokens
    CacheMissTokens=$r.prompt_cache_miss_tokens
    CompletionTokens=$r.completion_tokens
    TotalTokens=($r.prompt_cache_hit_tokens + $r.prompt_cache_miss_tokens + $r.completion_tokens)
    PeakCostCNY=$r.peak_cost_cny
    OffpeakCostCNY=$r.offpeak_cost_cny
    SemanticQuality=$r.semantic_quality
} | Format-List