$ErrorActionPreference = 'Stop'

$RunId = 'v1-20261104-a31860f-02'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot "evidence\v1\$RunId"
$auditPath = Join-Path $Evidence '07-demo\demo-normal-02.audit.jsonl'

if (-not (Test-Path $auditPath)) {
    throw "审计文件不存在: $auditPath"
}

$record = @(
    Get-Content -Encoding UTF8 $auditPath |
    ForEach-Object { $_ | ConvertFrom-Json }
) | Select-Object -Last 1

Clear-Host
Write-Host '=== V1 DEMO 04: AUDIT RECORD ==='
Write-Host "AUDIT FILE: $auditPath"
Write-Host ''

[pscustomobject]@{
    audit_id         = $record.audit_id
    timestamp        = $record.timestamp
    model_version    = $record.provenance.model_version
    prompt_version   = $record.provenance.prompt_version
    candidate_count  = $record.candidate_count
    context_tokens   = $record.context_tokens
    compliance_ok    = $record.compliance.approved
    compliance_steps = ($record.compliance.steps -join ' -> ')
    final_kind       = $record.final.kind
    final_ad_id      = $record.final.ad_id
} | Format-List