$ErrorActionPreference = 'Stop'

$RunId = 'v1-20261104-a31860f-02'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot "evidence\v1\$RunId"

$checks = @(
    @{
        Name = 'Ruff'
        File = 'ruff.stdout.txt'
        Pattern = 'All checks passed'
    },
    @{
        Name = 'mypy'
        File = 'mypy.stdout.txt'
        Pattern = 'Success: no issues found'
    },
    @{
        Name = 'Dependencies'
        File = 'dependencies.stdout.txt'
        Pattern = 'PASS'
    },
    @{
        Name = 'Schema'
        File = 'schema.stdout.txt'
        Pattern = 'PASS'
    },
    @{
        Name = 'Fitness'
        File = 'fitness.stdout.txt'
        Pattern = 'PASS'
    },
    @{
        Name = 'Repo completeness'
        File = 'repo-completeness.stdout.txt'
        Pattern = 'PASS'
    }
)

$summary = foreach ($check in $checks) {
    $path = Join-Path $Evidence $check.File

    if (-not (Test-Path $path)) {
        throw "静态检查证据不存在: $path"
    }

    $matched = Select-String `
        -Path $path `
        -Pattern $check.Pattern `
        -SimpleMatch `
        -Quiet

    [pscustomobject]@{
        Check = $check.Name
        Result = if ($matched) { 'PASS' } else { 'FAIL' }
        Evidence = $check.File
    }
}

Clear-Host
Write-Host '=== V1 DEMO 08: STATIC AND STRUCTURAL CHECKS ==='
Write-Host ''
$summary | Format-Table -AutoSize