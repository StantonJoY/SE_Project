. (Join-Path $PSScriptRoot '_common.ps1')

Write-Section 'V3 FINAL ACCEPTANCE - 05 REGRESSION, REPLAY, MUTATION'

$junit = Join-Path $EvidenceRoot '12-post-ruff\offline-full.junit.xml'
[xml]$xml = Get-Content -LiteralPath $junit -Raw -Encoding UTF8
Write-Host "FULL_TESTS=$($xml.testsuites.testsuite.tests)"
Write-Host "FULL_FAILURES=$($xml.testsuites.testsuite.failures)"
Write-Host "FULL_ERRORS=$($xml.testsuites.testsuite.errors)"

$replayRoot = Join-Path $RepoRoot 'evidence\v3\v3-20261120-4d0479f-01\09-replay'
foreach ($name in @('v1-replay','v2-replay','v3-replay')) {
    $path = Join-Path $replayRoot "$name.stdout.txt"
    Write-Host ''
    Write-Host "[$name]"
    Get-Content -LiteralPath $path -Tail 8 -Encoding UTF8
}

Write-Host ''
Write-Host '[mutation]'
Get-Content -LiteralPath (Join-Path $RepoRoot 'evidence\v3\v3-20261120-4d0479f-01\10-mutation\mutation.stdout.txt') -Encoding UTF8 |
    Select-Object -Last 8
