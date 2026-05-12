param(
  [double]$GoalUsd = 20,
  [int]$IntervalMinutes = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = (Resolve-Path (Join-Path $PSScriptRoot "continuous_until_10usd.ps1")).Path
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$args = @(
  "-NoProfile"
  "-ExecutionPolicy", "Bypass"
  "-File", "`"$scriptPath`""
  "-GoalUsd", "$GoalUsd"
  "-IntervalMinutes", "$IntervalMinutes"
)

$proc = Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
Write-Host "Started continuous loop process. PID=$($proc.Id)"
