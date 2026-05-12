param(
  [Parameter(Mandatory = $true)]
  [double]$AmountUsd,

  [Parameter(Mandatory = $true)]
  [string]$Client,

  [Parameter(Mandatory = $true)]
  [string]$Channel,

  [Parameter(Mandatory = $true)]
  [string]$Package,

  [string]$Note = "",
  [double]$GoalUsd = 10,
  [string]$TrackerFile = "tools/monetization/revenue_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($AmountUsd -le 0) {
  throw "AmountUsd must be > 0."
}

if (-not (Test-Path -LiteralPath $TrackerFile)) {
  throw "Tracker file not found: $TrackerFile"
}

$safeNote = $Note.Replace("`r", " ").Replace("`n", " ").Replace(",", ";")
$safeClient = $Client.Replace(",", ";")
$safeChannel = $Channel.Replace(",", ";")
$safePackage = $Package.Replace(",", ";")
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$line = "$timestamp,$AmountUsd,$safeClient,$safeChannel,$safePackage,$safeNote"
Add-Content -LiteralPath $TrackerFile -Value $line

$rows = @(Import-Csv -LiteralPath $TrackerFile)
$total = 0.0
foreach ($row in $rows) {
  if ($row.amount_usd -ne $null -and "$($row.amount_usd)".Trim() -ne "") {
    $total += [double]$row.amount_usd
  }
}

$remaining = [Math]::Round([Math]::Max(0, $GoalUsd - [double]$total), 2)
$totalRounded = [Math]::Round([double]$total, 2)

Write-Host ("Recorded payment: `${0} from {1}" -f $AmountUsd, $Client)
Write-Host ("Total: `${0}" -f $totalRounded)
if ($remaining -le 0) {
  Write-Host ("Goal reached: Total >= `${0}" -f $GoalUsd)
} else {
  Write-Host ("Remaining to goal `${0}: `${1}" -f $GoalUsd, $remaining)
}
