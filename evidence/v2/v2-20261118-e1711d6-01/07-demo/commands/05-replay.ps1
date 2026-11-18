$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
$v1 = Get-Content -Encoding UTF8 (Join-Path $Evidence 'v1-replay.stdout.txt')
$v2 = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'v2-replay.json') | ConvertFrom-Json
Clear-Host
Write-Host '=== V2 DEMO 05: FIXED REPLAY ==='
[pscustomobject]@{
    V1_MUST_PASS=($v1 | Select-String 'MUST_PASS 11/11').Line
    V1_MUST_FAIL=($v1 | Select-String 'MUST_FAIL 14/14').Line
    V1_Violations=($v1 | Select-String '违规 0 项').Line
    V2_CaseCount=$v2.case_count
    V2_Positive=$v2.positive_count
    V2_Negative=$v2.negative_count
    V2_ViolationCount=$v2.violation_count
    V2_Passed=$v2.passed
    V2_Provider=$v2.provider
    V2_LiveProviderTested=$v2.live_provider_tested
} | Format-List