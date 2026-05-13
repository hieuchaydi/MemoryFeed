param(
  [Parameter(Mandatory = $true)]
  [string]$ClientName,

  [Parameter(Mandatory = $true)]
  [ValidateSet("facebook","zalo","linkedin","community","github")]
  [string]$SourceChannel,

  [string]$ContactChannel = "",
  [double]$OfferPriceUsd = 10,
  [string]$Note = "direct-lead",
  [string]$LeadsFile = "tools/monetization/leads_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

Ensure-LeadsTrackerSchema -LeadsFile $LeadsFile

$rows = @(Import-Csv -LiteralPath $LeadsFile)
$slug = ($ClientName.ToLower() -replace "[^a-z0-9]+", "-").Trim("-")
if ($slug -eq "") { $slug = "lead" }

$contact = $ContactChannel
if ($contact.Trim() -eq "") { $contact = $SourceChannel }

$id = "direct/{0}/{1}-{2}" -f $SourceChannel, $slug, (Get-Date -Format "yyyyMMddHHmmss")
$now = (Get-Date).ToUniversalTime()
$nowUtc = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
$nextUtc = $now.AddMinutes(30).ToString("yyyy-MM-ddTHH:mm:ssZ")
$safeNote = Convert-ToSafeCsvField -Value $Note

$rows += [PSCustomObject]@{
  repo            = $id
  owner           = "direct"
  name            = $slug
  stage           = "new"
  last_action_utc = $nowUtc
  next_action_utc = $nextUtc
  offer_price_usd = [Math]::Round($OfferPriceUsd, 2)
  source_channel  = $SourceChannel
  contact_channel = $contact
  notes           = $safeNote
}

$rows | Export-Csv -LiteralPath $LeadsFile -NoTypeInformation
Write-Host "Added direct lead: $id"
