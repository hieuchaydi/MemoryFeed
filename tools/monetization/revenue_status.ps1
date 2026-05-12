param(
  [double]$GoalUsd = 20,
  [string]$TrackerFile = "tools/monetization/revenue_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

if (-not (Test-Path -LiteralPath $TrackerFile)) {
  throw "Tracker file not found: $TrackerFile"
}

$totals = Get-RevenueTotals -TrackerFile $TrackerFile
$remaining = [Math]::Round([Math]::Max(0, $GoalUsd - [double]$totals.ValidatedTotal), 2)

Write-Host "Payments count: $($totals.Count)"
Write-Host "Validated payments count: $($totals.ValidatedCount)"
Write-Host ("Total USD (all): `${0}" -f $totals.Total)
Write-Host ("Total USD (validated): `${0}" -f $totals.ValidatedTotal)
Write-Host ("Goal USD: `${0}" -f $GoalUsd)

if ($remaining -le 0) {
  Write-Host "Status: GOAL_REACHED"
} else {
  Write-Host "Status: IN_PROGRESS"
  Write-Host ("Remaining USD: `${0}" -f $remaining)
}
