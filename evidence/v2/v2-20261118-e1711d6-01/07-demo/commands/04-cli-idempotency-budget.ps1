$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
$after = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'cli-after-idempotent.txt') | ConvertFrom-Json
$final = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'cli-final-db.txt') | ConvertFrom-Json
$hashEqual = (Get-FileHash (Join-Path $Evidence 'cli-normal-1.stdout.json')).Hash -eq (Get-FileHash (Join-Path $Evidence 'cli-duplicate.stdout.json')).Hash
$ad1 = @($final.budgets | Where-Object { $_[0] -eq 'ad_001' })[0]
$ad2 = @($final.budgets | Where-Object { $_[0] -eq 'ad_002' })[0]
Clear-Host
Write-Host '=== V2 DEMO 04: IDEMPOTENCY AND BUDGET ==='
[pscustomobject]@{
    Evidence='cli-after-idempotent.txt, cli-final-db.txt'
    DuplicateOutputsByteEqual=$hashEqual
    AuditAfterFirstRequest=$after.audit_count
    RequestsAfterFirstRequest=@($after.requests).Count
    Ad001SpentCents=$ad1[2]
    Ad001RemainingCents=$ad1[3]
    Ad001Status=$ad1[4]
    Ad002SpentCents=$ad2[2]
    Ad002RemainingCents=$ad2[3]
    Ad002Status=$ad2[4]
    FinalAuditCount=$final.audit_count
    FinalRequestCount=@($final.requests).Count
    TotalSpendCents=($ad1[2]+$ad2[2])
} | Format-List