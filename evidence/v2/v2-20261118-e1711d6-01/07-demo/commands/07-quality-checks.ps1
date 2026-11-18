$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
$coverageLine = (Select-String -Path (Join-Path $Evidence 'bidding-coverage.stdout.txt') -Pattern 'Total coverage:').Line
$performanceText = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'performance.stdout.txt')
$mutationText = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'mutation.stdout.txt')
Clear-Host
Write-Host '=== V2 DEMO 07: QUALITY CHECKS ==='
[pscustomobject]@{
    CoverageEvidence='bidding-coverage.stdout.txt'
    Coverage=$coverageLine
    CoverageThreshold='90%'
    PerformanceEvidence='performance.stdout.txt'
    PerformanceResult=if($performanceText -match '1 passed'){'PASS'}else{'UNKNOWN'}
    PerformanceCase='100 candidates median below 50ms'
    MutationEvidence='mutation.stdout.txt'
    MutationResult=if($mutationText -match '25 条变异全部被检出'){'PASS 25/25'}else{'UNKNOWN'}
} | Format-List