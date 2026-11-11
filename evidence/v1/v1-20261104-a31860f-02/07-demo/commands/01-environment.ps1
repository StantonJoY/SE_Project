$ErrorActionPreference = 'Stop'

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Clear-Host
Write-Host '=== V1 DEMO 01: ENVIRONMENT ==='
Write-Host ''

[pscustomobject]@{
    Branch                   = (git branch --show-current).Trim()
    Commit                   = (git rev-parse HEAD).Trim()
    Python                  = (python --version 2>&1)
    App_Module              = (python -c "import app; print(app.__file__)").Trim()
    Ads_Module              = (python -c "import ads; print(ads.__file__)").Trim()
    Audit_Module            = (python -c "import audit; print(audit.__file__)").Trim()
    Compliance_Module       = (python -c "import compliance; print(compliance.__file__)").Trim()
    Selector_Module         = (python -c "import selector; print(selector.__file__)").Trim()
    Editable_Project        = (
        python -m pip show ad-recommender |
        Select-String '^Editable project location:' |
        ForEach-Object { $_.Line.Split(':', 2)[1].Trim() }
    )
} | Format-List