$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$Evidence = Join-Path $RepoRoot 'evidence\v2\v2-20261118-e1711d6-01'
Clear-Host
Write-Host '=== V2 DEMO 01: ENVIRONMENT ==='
[pscustomobject]@{
    Branch=(git -C $RepoRoot branch --show-current).Trim()
    EvidenceHead=(git -C $RepoRoot rev-parse HEAD).Trim()
    TestedCodeCommit='e1711d641077ad9be29ad44bde1580d5d8b219d5'
    Python=(python --version 2>&1)
    PythonPrefix=((python -c 'import sys; print(sys.prefix)').Trim())
    EditableProject=((python -m pip show ad-recommender | Select-String '^Editable project location:').Line -split ':',2 | Select-Object -Last 1).Trim()
    AppModule=(python -c 'import app; print(app.__file__)').Trim()
    BiddingModule=(python -c 'import bidding; print(bidding.__file__)').Trim()
} | Format-List