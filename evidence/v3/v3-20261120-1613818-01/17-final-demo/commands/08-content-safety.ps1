. (Join-Path $PSScriptRoot '_common.ps1')

Write-Section 'V3 FINAL ACCEPTANCE - 08 CONTENT SAFETY'

$result = Invoke-DemoPython 'v3-compliance' @(
    '-m','pytest','test/offline/test_v3_compliance.py',
    '-q','-p','no:cacheprovider'
)

Write-Host "COMPLIANCE_EXIT=$($result.ExitCode)"
if ($result.ExitCode -eq 0) {
    Write-Host 'COMPLIANCE_RESULT=PASS'
} else {
    Write-Host 'COMPLIANCE_RESULT=FAIL'
}
Get-Content -LiteralPath $result.Stdout -Tail 20 -Encoding UTF8
Get-Content -LiteralPath $result.Stderr -Tail 20 -Encoding UTF8
