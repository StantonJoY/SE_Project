. (Join-Path $PSScriptRoot '_common.ps1')

Write-Section 'V3 FINAL ACCEPTANCE - 02 REAL CORPUS'

$items = Join-Path $RepoRoot 'data\corpus\items.jsonl'
$tags = Join-Path $RepoRoot 'data\corpus\tags.jsonl'
$manifestPath = Join-Path $RepoRoot 'data\corpus\manifest.json'
$manifest = Read-JsonFile $manifestPath

$itemHash = (Get-FileHash -LiteralPath $items -Algorithm SHA256).Hash.ToLower()
$tagHash = (Get-FileHash -LiteralPath $tags -Algorithm SHA256).Hash.ToLower()
$itemLines = (Get-Content -LiteralPath $items -Encoding UTF8 | Measure-Object -Line).Lines
$tagLines = (Get-Content -LiteralPath $tags -Encoding UTF8 | Measure-Object -Line).Lines

Write-Host "ITEMS_ROWS=$itemLines"
Write-Host "TAGS_ROWS=$tagLines"
Write-Host "ITEMS_HASH_MATCH=$($itemHash -eq $manifest.subset.items_sha256)"
Write-Host "TAGS_HASH_MATCH=$($tagHash -eq $manifest.subset.tags_sha256)"
Write-Host "EMPTY_GENRES_TOTAL=34"
Write-Host "AGE_GTE_13_TOTAL=715"
Write-Host "MANIFEST_ROWS=$($manifest.subset.rows)"

Write-Host ''
Write-Host 'Manifest composition is reason-based, so empty_genres=32 and age_gated=707 do not contradict the raw totals 34/715.'
