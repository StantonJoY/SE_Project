$ErrorActionPreference = 'Stop'

$RunId = 'v1-20261104-a31860f-02'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot "evidence\v1\$RunId"
$DemoRoot = Join-Path $Evidence '07-demo'

$stdoutPath = Join-Path $DemoRoot 'demo-normal-02.stdout.json'
$stderrPath = Join-Path $DemoRoot 'demo-normal-02.stderr.txt'
$auditPath  = Join-Path $DemoRoot 'demo-normal-02.audit.jsonl'

foreach ($path in @($stdoutPath, $stderrPath, $auditPath)) {
    if (-not (Test-Path $path)) {
        throw "演示证据不存在: $path"
    }
}

$stdoutText = Get-Content -Raw -Encoding UTF8 $stdoutPath
$stderrText = Get-Content -Raw -Encoding UTF8 $stderrPath
$auditLines = @(Get-Content -Encoding UTF8 $auditPath)

Clear-Host
Write-Host '=== V1 DEMO 03: NORMAL RECOMMENDATION ==='
Write-Host 'COMMAND: python -m app --time-slot night --device mobile --tag student'
Write-Host 'RECORDED_EXIT_CODE=0'
Write-Host ''
Write-Host 'RESULT:'
Write-Host $stdoutText
Write-Host 'AUDIT ID:'
Write-Host $stderrText
Write-Host "AUDIT_LINES=$($auditLines.Count)"