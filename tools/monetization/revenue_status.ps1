param(
  [double]$GoalUsd = 10,
  [string]$TrackerFile = "tools/monetization/revenue_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $TrackerFile)) {
  throw "Tracker file not found: $TrackerFile"
}

$rows = @(Import-Csv -LiteralPath $TrackerFile)
$count = @($rows).Count
$total = 0.0
foreach ($row in $rows) {
  if ($row.amount_usd -ne $null -and "$($row.amount_usd)".Trim() -ne "") {
    $total += [double]$row.amount_usd
  }
}

$totalRounded = [Math]::Round([double]$total, 2)
$remaining = [Math]::Round([Math]::Max(0, $GoalUsd - [double]$total), 2)

Write-Host "Payments count: $count"
Write-Host ("Total USD: `${0}" -f $totalRounded)
Write-Host ("Goal USD: `${0}" -f $GoalUsd)

if ($remaining -le 0) {
  Write-Host "Status: GOAL_REACHED"
} else {
  Write-Host "Status: IN_PROGRESS"
  Write-Host ("Remaining USD: `${0}" -f $remaining)
}
