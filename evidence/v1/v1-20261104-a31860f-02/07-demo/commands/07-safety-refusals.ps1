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
Write-Host '=== V1 DEMO 07: SAFETY AND COMPLIANCE REFUSALS ==='
Write-Host ''

$report.outcomes |
    Where-Object {
        $_.id -in @(
            'EC-007',
            'EC-008',
            'EC-009',
            'EC-010',
            'EC-011',
            'EC-012'
        )
    } |
    Select-Object `
        id,
        label,
        expected,
        expected_reason,
        actual_reason,
        matched,
        audit_records,
        @{Name = 'violations'; Expression = { @($_.violations).Count }} |
    Format-Table -AutoSize