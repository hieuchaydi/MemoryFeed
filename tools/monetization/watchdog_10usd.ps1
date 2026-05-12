param(
  [double]$GoalUsd = 20,
  [int]$RunnerIntervalMinutes = 10,
  [int]$WatchIntervalSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$trackerFile = Join-Path $repoRoot "tools/monetization/revenue_tracker.csv"
$startRunnerScript = Join-Path $repoRoot "tools/monetization/start_continuous_10usd.ps1"
$stopRunnerScript = Join-Path $repoRoot "tools/monetization/stop_continuous_10usd.ps1"
$watchdogLog = Join-Path $repoRoot "tools/monetization/watchdog_10usd.log"

if (-not (Test-Path -LiteralPath $trackerFile)) { throw "Missing tracker file: $trackerFile" }
if (-not (Test-Path -LiteralPath $startRunnerScript)) { throw "Missing start script: $startRunnerScript" }
if (-not (Test-Path -LiteralPath $stopRunnerScript)) { throw "Missing stop script: $stopRunnerScript" }

function Get-RunnerCount {
  $procs = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -like "*continuous_until_10usd.ps1*" })
  return @($procs).Count
}

Write-Host "Watchdog started. Goal=$GoalUsd"

while ($true) {
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $totals = Get-RevenueTotals -TrackerFile $trackerFile

  if ($totals.ValidatedTotal -ge $GoalUsd) {
    Add-Content -LiteralPath $watchdogLog -Value "$ts total=$($totals.Total) validated_total=$($totals.ValidatedTotal) goal=$GoalUsd action=goal_reached_stop_runner"
    Push-Location $repoRoot
    try {
      & powershell -ExecutionPolicy Bypass -File $stopRunnerScript
    } finally {
      Pop-Location
    }
    break
  }

  $runnerCount = Get-RunnerCount
  if ($runnerCount -eq 0) {
    Add-Content -LiteralPath $watchdogLog -Value "$ts total=$($totals.Total) validated_total=$($totals.ValidatedTotal) action=runner_missing_restart"
    Push-Location $repoRoot
    try {
      & powershell -ExecutionPolicy Bypass -File $startRunnerScript -GoalUsd $GoalUsd -IntervalMinutes $RunnerIntervalMinutes
    } finally {
      Pop-Location
    }
  } else {
    Add-Content -LiteralPath $watchdogLog -Value "$ts total=$($totals.Total) validated_total=$($totals.ValidatedTotal) action=runner_ok count=$runnerCount"
  }

  Start-Sleep -Seconds ([Math]::Max(30, $WatchIntervalSeconds))
}

Write-Host "Watchdog exited (goal reached)."
