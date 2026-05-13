param(
  [double]$GoalUsd = 20,
  [int]$IntervalMinutes = 15,
  [int]$MaxCycles = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$trackerFile = Join-Path $repoRoot "tools/monetization/revenue_tracker.csv"
$pipelineScript = Join-Path $repoRoot "tools/monetization/run_10usd_pipeline.ps1"
$logFile = Join-Path $repoRoot "tools/monetization/continuous_runner.log"

if (-not (Test-Path -LiteralPath $trackerFile)) { throw "Missing tracker file: $trackerFile" }
if (-not (Test-Path -LiteralPath $pipelineScript)) { throw "Missing pipeline script: $pipelineScript" }

$cycle = 0
Write-Host "Starting continuous revenue loop. Goal=$GoalUsd, IntervalMinutes=$IntervalMinutes"

while ($true) {
  $cycle += 1
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $totals = Get-RevenueTotals -TrackerFile $trackerFile
  $remaining = [Math]::Round([Math]::Max(0, $GoalUsd - $totals.ValidatedTotal), 2)
  $logLine = "$ts cycle=$cycle total=$($totals.Total) validated_total=$($totals.ValidatedTotal) goal=$GoalUsd remaining=$remaining"
  Add-Content -LiteralPath $logFile -Value $logLine
  Write-Host $logLine

  if ($totals.ValidatedTotal -ge $GoalUsd) {
    Write-Host "Goal reached. Exiting loop."
    break
  }

  try {
    Push-Location $repoRoot
    & powershell -ExecutionPolicy Bypass -File $pipelineScript -GoalUsd $GoalUsd
  } catch {
    $err = $_.Exception.Message.Replace("`r", " ").Replace("`n", " ")
    Add-Content -LiteralPath $logFile -Value "$ts cycle=$cycle pipeline_error=$err"
    Write-Warning "Pipeline error: $err"
  } finally {
    Pop-Location
  }

  if ($MaxCycles -gt 0 -and $cycle -ge $MaxCycles) {
    Write-Host "Reached MaxCycles=$MaxCycles. Exiting loop."
    break
  }

  $sleepSeconds = [Math]::Max(60, $IntervalMinutes * 60)
  Start-Sleep -Seconds $sleepSeconds
}
