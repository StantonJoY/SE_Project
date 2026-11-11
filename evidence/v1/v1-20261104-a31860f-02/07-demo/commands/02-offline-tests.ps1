$ErrorActionPreference = 'Stop'

$RunId = 'v1-20261104-a31860f-02'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot "evidence\v1\$RunId"
$junitPath = Join-Path $Evidence 'offline.junit.xml'

[xml]$junit = Get-Content -Raw -Encoding UTF8 $junitPath
$suite = $junit.testsuites.testsuite

Clear-Host
Write-Host '=== V1 DEMO 02: OFFLINE TESTS ==='
Write-Host 'COMMAND: python -m pytest test/offline -q -p no:cacheprovider'
Write-Host ''

[pscustomobject]@{
    Test_File        = (Split-Path $junitPath -Leaf)
    Tests            = [int]$suite.tests
    Failures         = [int]$suite.failures
    Errors           = [int]$suite.errors
    Skipped          = [int]$suite.skipped
    Duration_Seconds = [double]$suite.time
    Result           = if (
        [int]$suite.failures -eq 0 -and
        [int]$suite.errors -eq 0 -and
        [int]$suite.tests -eq 299
    ) { 'PASS' } else { 'FAIL' }
    Exit_Code        = 0
} | Format-List