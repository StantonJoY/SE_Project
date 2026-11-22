. (Join-Path $PSScriptRoot '_common.ps1')

Write-Section 'V3 FINAL ACCEPTANCE - 01 BASELINE'

Set-Location $RepoRoot

$branch = (git branch --show-current).Trim()
$head = (git rev-parse HEAD).Trim()

Write-Host "BRANCH=$branch"
Write-Host "WORKTREE_HEAD=$head"
Write-Host 'TESTED_CODE_COMMIT=161381887e421a121cd2878fcbf397d42a8ac818'
Write-Host "DOCS_EVIDENCE_COMMIT=$head"
Write-Host "PYTHON_VERSION=$((python --version 2>&1).Trim())"
Write-Host "CONDA_PREFIX=$env:CONDA_PREFIX"
python -m pip show ad-recommender | Select-String 'Editable project location:'

Write-Host ''
Write-Host 'NOTE: current HEAD is the docs/evidence commit; tested code remains 1613818.'
