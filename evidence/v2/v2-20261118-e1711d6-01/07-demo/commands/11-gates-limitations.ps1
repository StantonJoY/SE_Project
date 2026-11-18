$ErrorActionPreference = 'Stop'
Clear-Host
Write-Host '=== V2 DEMO 11: GATES, LIMITATIONS, CONCLUSION ==='
[pscustomobject]@{
    Gate1_TestApproval='FAIL - 10 V2 test files lack human pre-approval'
    Gate2_StaticAnalysis='PASS'
    Gate3_Schema='PASS'
    Gate4_SemanticEvaluation='PASS'
    Gate5_Regression='PASS 617'
    Gate6_AIUseLog='PASS'
    BranchProtection='NOT VERIFIED'
    OfflineResult='PASS'
    LiveOperational='PASS'
    LivePerformance='PASS p95=2.426s'
    LiveCost='ESTIMATED'
    LiveSemanticQuality='PENDING HUMAN LABELS'
    CourseReadiness='CHANGES REQUIRED'
} | Format-List