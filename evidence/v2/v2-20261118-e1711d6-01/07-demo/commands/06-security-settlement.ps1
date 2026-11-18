$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
$v2 = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'v2-replay.json') | ConvertFrom-Json
Clear-Host
Write-Host '=== V2 DEMO 06: SECURITY AND SETTLEMENT BOUNDARIES ==='
$v2.cases |
    Where-Object {
        $_.id -in @(
            'V2-007-compliance',
            'V2-010-bool-score',
            'V2-011-outside-set',
            'V2-014-after-debit',
            'V2-015-before-audit',
            'V2-016-before-commit',
            'V2-017-request-conflict',
            'V2-018-invalid-bid'
        )
    } |
    Select-Object id,label,matched,@{Name='violations';Expression={@($_.violations).Count}} |
    Format-Table -AutoSize
Write-Host ''
[pscustomobject]@{
    ComplianceEscapeCount=$v2.compliance_escape_count
    TotalViolationCount=$v2.violation_count
    AllCasesPassed=$v2.passed
} | Format-List