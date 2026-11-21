. (Join-Path $PSScriptRoot '_common.ps1')

Write-Section 'V3 FINAL ACCEPTANCE - 09 STATIC CHECKS AND COVERAGE'

$staticRoot = Join-Path $EvidenceRoot '14-final-static'
Write-Host '[final static artifacts]'
Get-ChildItem -LiteralPath $staticRoot -Filter '*.stdout.txt' |
    Select-Object -ExpandProperty BaseName |
    Sort-Object

Write-Host ''
Write-Host '[coverage summary]'
Get-Content -LiteralPath (Join-Path $EvidenceRoot '15-coverage\v3-coverage.stdout.txt') -Tail 30 -Encoding UTF8
