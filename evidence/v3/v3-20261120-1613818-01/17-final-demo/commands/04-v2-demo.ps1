. (Join-Path $PSScriptRoot '_common.ps1')

Write-Section 'V3 FINAL ACCEPTANCE - 04 V2 AUCTION AND BUDGET'

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$requestId = "v3-final-$stamp"
$db = Join-Path $DemoDir "v2-$stamp.sqlite3"

$first = Invoke-DemoPython 'v2-first' @(
    '-m','app.cli_v2','--corpus','--request-id',$requestId,
    '--time-slot','afternoon','--device','desktop','--tag','family','--db',$db
)
Write-Host "FIRST_EXIT=$($first.ExitCode)"
Show-JsonSummary 'FIRST' $first.Stdout

$replay = Invoke-DemoPython 'v2-replay' @(
    '-m','app.cli_v2','--corpus','--request-id',$requestId,
    '--time-slot','afternoon','--device','desktop','--tag','family','--db',$db
)
Write-Host "REPLAY_EXIT=$($replay.ExitCode)"
$firstHash = (Get-FileHash $first.Stdout -Algorithm SHA256).Hash
$replayHash = (Get-FileHash $replay.Stdout -Algorithm SHA256).Hash
$hashEqual = $firstHash -eq $replayHash
Write-Host "REPLAY_HASH_EQUAL=$hashEqual"

$conflict = Invoke-DemoPython 'v2-conflict' @(
    '-m','app.cli_v2','--corpus','--request-id',$requestId,
    '--time-slot','night','--device','mobile','--tag','gamer','--db',$db
)
Write-Host "CONFLICT_EXIT=$($conflict.ExitCode)"
Show-JsonSummary 'CONFLICT' $conflict.Stdout

$dbScript = Join-Path $DemoDir 'v2-db-summary.py'
$dbCode = @'
import json
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
requests = db.execute(
    "SELECT request_id, ad_id, charge_cents FROM requests ORDER BY rowid"
).fetchall()
selected = {row[1] for row in requests if row[1]}
rows = db.execute(
    "SELECT ad_id, total_cents, spent_cents, remaining_cents, status "
    "FROM budget ORDER BY ad_id"
).fetchall()
rows = [row for row in rows if row[0] in selected]
print(json.dumps({
    "audit_count": db.execute("SELECT COUNT(*) FROM audit").fetchone()[0],
    "requests": requests,
    "selected_budgets": rows,
}, ensure_ascii=False, indent=2))
'@
$dbCode | Set-Content -LiteralPath $dbScript -Encoding UTF8
$dbResult = Invoke-DemoPython 'v2-db-summary' @($dbScript, $db)
Get-Content $dbResult.Stdout -Raw -Encoding UTF8
