$ErrorActionPreference = 'Stop'

$RunId = 'v1-20261104-a31860f-02'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot "evidence\v1\$RunId"
$evalPath = Join-Path $Evidence 'eval-replay.json'

if (-not (Test-Path $evalPath)) {
    throw "评估报告不存在: $evalPath"
}

$report = Get-Content -Raw -Encoding UTF8 $evalPath | ConvertFrom-Json

Clear-Host
Write-Host '=== V1 DEMO 06: FIXED EVALUATION SET ==='
Write-Host "REPORT: $evalPath"
Write-Host ''

[pscustomobject]@{
    MUST_PASS           = "$($report.must_pass_met)/$($report.must_pass_total)"
    MUST_FAIL           = "$($report.must_fail_met)/$($report.must_fail_total)"
    KNOWN_FAILURES      = $report.known_failure_total
    VIOLATIONS          = @($report.violations).Count
    P95_LATENCY_SECONDS = $report.p95_latency_sec
    SLA_DRIFT_ALERT     = $report.sla_drift_alert
    FINAL_RESULT        = $report.passed
} | Format-List