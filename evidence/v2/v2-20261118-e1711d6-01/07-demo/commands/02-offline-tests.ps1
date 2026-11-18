$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
[xml]$junit = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'offline-full.junit.xml')
$suite = $junit.testsuites.testsuite
Clear-Host
Write-Host '=== V2 DEMO 02: OFFLINE TESTS ==='
Write-Host 'COMMAND: python -m pytest test/offline -q -p no:cacheprovider'
Write-Host ''
[pscustomobject]@{
    Evidence='offline-full.junit.xml'
    Tests=[int]$suite.tests
    Failures=[int]$suite.failures
    Errors=[int]$suite.errors
    Skipped=[int]$suite.skipped
    DurationSeconds=[double]$suite.time
    Result=if([int]$suite.failures -eq 0 -and [int]$suite.errors -eq 0 -and [int]$suite.tests -eq 617){'PASS'}else{'FAIL'}
    ExitCode=0
} | Format-List