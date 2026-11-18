$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
$demo = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'v2-demo-clean.stdout.json') | ConvertFrom-Json
Clear-Host
Write-Host '=== V2 DEMO 03: SEVEN SCENARIOS ==='
[pscustomobject]@{
    Evidence='v2-demo-clean.stdout.json'
    Provider=$demo.provider
    LiveProviderTested=$demo.live_provider_tested
    ScenarioCount=$demo.scenario_count
    Passed=$demo.passed
    MainAuditCount=$demo.main_audit_count
    TotalObservedSpendCents=$demo.total_observed_spend_cents
} | Format-List
Write-Host ''
$demo.scenarios | Select-Object -ExpandProperty scenario | ForEach-Object { "- $_" }