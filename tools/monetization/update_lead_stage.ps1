param(
  [Parameter(Mandatory = $true)]
  [string]$Repo,

  [Parameter(Mandatory = $true)]
  [ValidateSet("new","contacted","replied","negotiating","won","lost")]
  [string]$Stage,

  [string]$Note = "",
  [int]$NextActionHours = 24,
  [int]$NextActionMinutes = -1,
  [double]$OfferPriceUsd = -1,
  [string]$SourceChannel = "",
  [string]$ContactChannel = "",
  [string]$LeadsFile = "tools/monetization/leads_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

Ensure-LeadsTrackerSchema -LeadsFile $LeadsFile

$rows = @(Import-Csv -LiteralPath $LeadsFile)
$found = $false
$now = (Get-Date).ToUniversalTime()
$nowUtc = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
$nextUtc = ""
if ($NextActionMinutes -ge 0) {
  $nextUtc = $now.AddMinutes($NextActionMinutes).ToString("yyyy-MM-ddTHH:mm:ssZ")
} else {
  $nextUtc = $now.AddHours($NextActionHours).ToString("yyyy-MM-ddTHH:mm:ssZ")
}
$safeNote = Convert-ToSafeCsvField -Value $Note

foreach ($row in $rows) {
  if ($row.repo -eq $Repo) {
    $row.stage = $Stage
    $row.last_action_utc = $nowUtc
    if ($Stage -eq "won" -or $Stage -eq "lost") {
      $row.next_action_utc = ""
    } else {
      $row.next_action_utc = $nextUtc
    }
    if ($OfferPriceUsd -ge 0) {
      $row.offer_price_usd = [Math]::Round($OfferPriceUsd, 2)
    }
    if ("$SourceChannel".Trim() -ne "") {
      $row.source_channel = Convert-ToSafeCsvField -Value $SourceChannel
    }
    if ("$ContactChannel".Trim() -ne "") {
      $row.contact_channel = Convert-ToSafeCsvField -Value $ContactChannel
    }
    if ($safeNote -ne "") {
      $row.notes = $safeNote
    }
    $found = $true
    break
  }
}

if (-not $found) {
  throw "Repo not found in leads tracker: $Repo"
}

$rows | Export-Csv -LiteralPath $LeadsFile -NoTypeInformation
Write-Host "Updated: $Repo -> $Stage"
