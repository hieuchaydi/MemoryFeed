param(
  [double]$GoalUsd = 10,
  [int]$RunnerIntervalMinutes = 10,
  [int]$WatchIntervalSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = (Resolve-Path (Join-Path $PSScriptRoot "watchdog_10usd.ps1")).Path
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$args = @(
  "-NoProfile"
  "-ExecutionPolicy", "Bypass"
  "-File", "`"$scriptPath`""
  "-GoalUsd", "$GoalUsd"
  "-RunnerIntervalMinutes", "$RunnerIntervalMinutes"
  "-WatchIntervalSeconds", "$WatchIntervalSeconds"
)

$proc = Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
Write-Host "Started watchdog process. PID=$($proc.Id)"
