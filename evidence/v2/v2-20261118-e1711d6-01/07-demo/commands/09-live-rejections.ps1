$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
$medical = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'live-medical-2.stdout.json') | ConvertFrom-Json
$bad = Get-Content -Raw -Encoding UTF8 (Join-Path $Evidence 'live-bad-key.stdout.json') | ConvertFrom-Json
$medicalSpent = [int](python -c "import sqlite3; db=sqlite3.connect(r'$($Evidence)\live-medical-02.sqlite3'); print(db.execute('SELECT COALESCE(SUM(spent_cents),0) FROM budget').fetchone()[0])")
$medicalAudit = [int](python -c "import sqlite3; db=sqlite3.connect(r'$($Evidence)\live-medical-02.sqlite3'); print(db.execute('SELECT COUNT(*) FROM audit').fetchone()[0])")
$badSpent = [int](python -c "import sqlite3; db=sqlite3.connect(r'$($Evidence)\live-bad-key.sqlite3'); print(db.execute('SELECT COALESCE(SUM(spent_cents),0) FROM budget').fetchone()[0])")
$badAudit = [int](python -c "import sqlite3; db=sqlite3.connect(r'$($Evidence)\live-bad-key.sqlite3'); print(db.execute('SELECT COUNT(*) FROM audit').fetchone()[0])")
Clear-Host
Write-Host '=== V2 DEMO 09: LIVE REJECTIONS ==='
[pscustomobject]@{
    MedicalKind=$medical.kind
    MedicalReason=$medical.reason_code
    MedicalSpentCents=$medicalSpent
    MedicalAuditCount=$medicalAudit
    BadKeyKind=$bad.kind
    BadKeyReason=$bad.reason_code
    BadKeySpentCents=$badSpent
    BadKeyAuditCount=$badAudit
} | Format-List