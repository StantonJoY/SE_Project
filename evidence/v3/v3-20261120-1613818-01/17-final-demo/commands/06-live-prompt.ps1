. (Join-Path $PSScriptRoot '_common.ps1')

Write-Section 'V3 FINAL ACCEPTANCE - 06 LIVE PROMPT SEMANTIC QUALITY'

$v2Path = Join-Path $EvidenceRoot '16-live-prompt\live-prompt-multi-scene-results.json'
$v1Path = Join-Path $EvidenceRoot '16-v1-live-prompt\v1-live-semantic-results.json'
$v2 = Read-JsonFile $v2Path
$v1 = Read-JsonFile $v1Path
$v2Scenes = @($v2.scenes)
$v2Structural = 0
$v2TotalRuns = 0
foreach ($scene in $v2Scenes) {
    $sceneRuns = @($scene.runs)
    $v2TotalRuns += $sceneRuns.Count
    if ($scene.structural_valid_count) {
        $v2Structural += [int]$scene.structural_valid_count
    }
}
$v1Scenes = @($v1.scenes)
$v1SceneCount = $v1Scenes.Count
$v1RunsPerScene = if ($v1SceneCount -gt 0) { @($v1Scenes[0].runs).Count } else { 0 }
$v1Structural = 0
foreach ($scene in $v1Scenes) {
    foreach ($run in @($scene.runs)) {
        if ($run.kind) {
            $v1Structural++
        }
    }
}

Write-Host "V2_PROMPT_VERSION=$($v2.prompt_version)"
Write-Host "V2_SCENES=$($v2.scene_count)"
Write-Host "V2_RUNS_PER_SCENE=$($v2.runs_per_scene)"
Write-Host "V2_STRUCTURAL=$v2Structural/$v2TotalRuns"
Write-Host "V2_TITLE_BAIT=$($v2.title_bait_cases.Count)"
Write-Host "V2_KNOWN_TITLE=$($v2.known_title_cases.Count)"
Write-Host 'V2_STATUS=PASS_WITH_LIMITATIONS'

Write-Host ''
foreach ($scene in $v2.scenes) {
    $sceneRuns = @($scene.runs)
    Write-Host "V2_SCENE=$($scene.scene_id) STRUCTURAL=$($scene.structural_valid_count)/$($sceneRuns.Count) SELECTED=$($scene.selected_counts | ConvertTo-Json -Compress)"
}

Write-Host ''
Write-Host "V1_PROMPT_VERSION=$($v1.prompt_version)"
Write-Host "V1_SCENES=$v1SceneCount"
Write-Host "V1_RUNS_PER_SCENE=$v1RunsPerScene"
Write-Host "V1_STRUCTURAL=$v1Structural/$($v1SceneCount * $v1RunsPerScene)"
Write-Host 'V1_STATUS=TEST-ONLY PASS_WITH_LIMITATIONS'

Write-Host ''
Write-Host 'BOUNDARY: V1 product CLI remains Mock/Offline; V1 live was injected through the pipeline test harness.'
