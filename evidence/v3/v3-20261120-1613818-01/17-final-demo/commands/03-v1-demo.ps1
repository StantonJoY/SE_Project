. (Join-Path $PSScriptRoot '_common.ps1')

Write-Section 'V3 FINAL ACCEPTANCE - 03 V1 CORPUS E2E'

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$normalAudit = Join-Path $DemoDir "v1-normal-$stamp.audit.jsonl"
$invalidAudit = Join-Path $DemoDir "v1-invalid-$stamp.audit.jsonl"

$normal = Invoke-DemoPython 'v1-normal' @(
    '-m','app','--corpus','--time-slot','night','--device','mobile','--tag','student',
    '--audit',$normalAudit
)
Write-Host "NORMAL_EXIT=$($normal.ExitCode)"
Show-JsonSummary 'NORMAL' $normal.Stdout
Show-AuditCount 'NORMAL_AUDIT_COUNT' $normalAudit
Get-Content $normal.Stderr -Raw -Encoding UTF8

$invalid = Invoke-DemoPython 'v1-invalid' @(
    '-m','app','--corpus','--time-slot','day','--device','mobile',
    '--audit',$invalidAudit
)
Write-Host "INVALID_EXIT=$($invalid.ExitCode)"
Show-JsonSummary 'INVALID' $invalid.Stdout
Show-AuditCount 'INVALID_AUDIT_COUNT' $invalidAudit
Get-Content $invalid.Stderr -Raw -Encoding UTF8
