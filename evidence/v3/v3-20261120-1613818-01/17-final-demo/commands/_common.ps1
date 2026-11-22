$ErrorActionPreference = 'Stop'

$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

if ($env:V3_REPO_ROOT) {
    $RepoRoot = (Resolve-Path -LiteralPath $env:V3_REPO_ROOT).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..\..')).Path
}

if ($env:V3_DEMO_DIR) {
    $DemoDir = (Resolve-Path -LiteralPath $env:V3_DEMO_DIR).Path
} else {
    $DemoDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
}

$EvidenceRoot = (Resolve-Path -LiteralPath (Join-Path $DemoDir '..')).Path
$Python = (Get-Command python).Source

function Write-Section {
    param([string]$Title)
    Write-Host ''
    Write-Host ('=' * 78) -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host ('=' * 78) -ForegroundColor Cyan
}

function Invoke-DemoPython {
    param(
        [string]$Name,
        [string[]]$Arguments
    )

    $stdout = Join-Path $DemoDir "$Name.stdout.txt"
    $stderr = Join-Path $DemoDir "$Name.stderr.txt"
    $proc = Start-Process `
        -FilePath $Python `
        -ArgumentList $Arguments `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr

    [pscustomobject]@{
        Name = $Name
        ExitCode = $proc.ExitCode
        Stdout = $stdout
        Stderr = $stderr
    }
}

function Read-JsonFile {
    param([string]$Path)
    Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Show-JsonSummary {
    param(
        [string]$Label,
        [string]$Path
    )
    $json = Read-JsonFile $Path
    Write-Host "$Label=$($json.kind)"
    if ($json.ad) {
        Write-Host "AD_ID=$($json.ad.ad_id)"
    }
    if ($json.reason_code) {
        Write-Host "REASON_CODE=$($json.reason_code)"
    }
    if ($json.auction) {
        Write-Host "BID_CENTS=$($json.auction.bid_cents)"
        Write-Host "PRICE_CENTS=$($json.auction.price_cents)"
    }
    Write-Host "AUDIT_ID=$($json.audit_id)"
}

function Show-AuditCount {
    param(
        [string]$Label,
        [string]$Path
    )
    if (Test-Path -LiteralPath $Path) {
        $count = (Get-Content -LiteralPath $Path -Encoding UTF8 | Measure-Object -Line).Lines
        Write-Host "$Label=$count"
    } else {
        Write-Host "$Label=NOT_FOUND"
    }
}
