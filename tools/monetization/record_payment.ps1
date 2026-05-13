param(
  [Parameter(Mandatory = $true)]
  [double]$AmountUsd,

  [Parameter(Mandatory = $true)]
  [string]$Client,

  [Parameter(Mandatory = $true)]
  [string]$Channel,

  [Parameter(Mandatory = $true)]
  [string]$Package,

  [Parameter(Mandatory = $true)]
  [string]$TransactionId,

  [Parameter(Mandatory = $true)]
  [string]$ProofRef,

  [string]$Note = "",
  [double]$GoalUsd = 20,
  [string]$TrackerFile = "tools/monetization/revenue_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

if ($AmountUsd -le 0) {
  throw "AmountUsd must be > 0."
}

if ("$TransactionId".Trim() -eq "") {
  throw "TransactionId is required."
}

if ("$ProofRef".Trim() -eq "") {
  throw "ProofRef is required."
}

Ensure-RevenueTrackerSchema -TrackerFile $TrackerFile

$safeNote = Convert-ToSafeCsvField -Value $Note
$safeClient = Convert-ToSafeCsvField -Value $Client
$safeChannel = Convert-ToSafeCsvField -Value $Channel
$safePackage = Convert-ToSafeCsvField -Value $Package
$safeTx = Convert-ToSafeCsvField -Value $TransactionId
$safeProof = Convert-ToSafeCsvField -Value $ProofRef
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$line = "$timestamp,$AmountUsd,$safeClient,$safeChannel,$safePackage,$safeTx,$safeProof,true,$safeNote"
Add-Content -LiteralPath $TrackerFile -Value $line

$totals = Get-RevenueTotals -TrackerFile $TrackerFile
$remaining = [Math]::Round([Math]::Max(0, $GoalUsd - [double]$totals.ValidatedTotal), 2)

Write-Host ("Recorded payment: `${0} from {1}" -f $AmountUsd, $Client)
Write-Host ("Total (all): `${0}" -f $totals.Total)
Write-Host ("Validated Total: `${0}" -f $totals.ValidatedTotal)
if ($remaining -le 0) {
  Write-Host ("Goal reached: Validated Total >= `${0}" -f $GoalUsd)
} else {
  Write-Host ("Remaining to goal `${0}: `${1}" -f $GoalUsd, $remaining)
}
