$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
$live = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'live-smoke-2.stdout.json') | ConvertFrom-Json
$hashEqual = (Get-FileHash (Join-Path $Evidence 'live-smoke-2.stdout.json')).Hash -eq (Get-FileHash (Join-Path $Evidence 'live-replay-2.stdout.json')).Hash
$budgetJson = python -c "import sqlite3,json; db=sqlite3.connect(r'$($Evidence)\live-02.sqlite3'); print(json.dumps({'budgets':db.execute('SELECT ad_id,total_cents,spent_cents,remaining_cents,status FROM budget ORDER BY ad_id').fetchall(),'audit_count':db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],'request_count':db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]}))"
$budget = $budgetJson | ConvertFrom-Json
Clear-Host
Write-Host '=== V2 DEMO 08: LIVE NORMAL AND IDEMPOTENT REPLAY ==='
[pscustomobject]@{
    Kind=$live.kind
    AdId=$live.ad.ad_id
    Relevance=$live.auction.relevance
    BidCents=$live.auction.bid_cents
    PriceCents=$live.auction.price_cents
    ReplayOutputHashEqual=$hashEqual
    AuditCount=$budget.audit_count
    RequestCount=$budget.request_count
    Budgets=($budget.budgets | ForEach-Object { "$($_[0]): spent=$($_[2]), remaining=$($_[3]), status=$($_[4])" }) -join '; '
} | Format-List