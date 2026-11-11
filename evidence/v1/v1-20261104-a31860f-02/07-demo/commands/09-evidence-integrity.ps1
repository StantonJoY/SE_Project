$ErrorActionPreference = 'Stop'

$RunId = 'v1-20261104-a31860f-02'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot "evidence\v1\$RunId"

$manifestPath = Join-Path $Evidence 'run-manifest.json'
$checksumPath = Join-Path $Evidence 'checksums.sha256'
$repoCompletenessPath = Join-Path $Evidence 'repo-completeness.stdout.txt'

foreach ($path in @($manifestPath, $checksumPath, $repoCompletenessPath)) {
    if (-not (Test-Path $path)) {
        throw "证据文件不存在: $path"
    }
}

$manifest = Get-Content -Raw -Encoding UTF8 $manifestPath | ConvertFrom-Json
$checksumLines = @(Get-Content -Encoding UTF8 $checksumPath)
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash

Clear-Host
Write-Host '=== V1 DEMO 09: REPOSITORY AND EVIDENCE INTEGRITY ==='
Write-Host ''

Write-Host 'REPOSITORY COMPLETENESS:'
Get-Content -Encoding UTF8 $repoCompletenessPath |
    Select-Object -Last 5

Write-Host ''
[pscustomobject]@{
    run_id                     = $manifest.run_id
    mode                       = $manifest.mode
    status                     = $manifest.status
    course_readiness           = $manifest.course_submission_readiness
    tests                      = "$($manifest.tests.passed)/$($manifest.tests.collected)"
    eval_violations            = $manifest.evaluation.violations
    checksum_files             = $checksumLines.Count
    manifest_sha256            = $manifestHash
} | Format-List