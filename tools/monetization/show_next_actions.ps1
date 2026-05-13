param(
  [int]$Limit = 10,
  [string]$LeadsFile = "tools/monetization/leads_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

Ensure-LeadsTrackerSchema -LeadsFile $LeadsFile

$rows = @(Import-Csv -LiteralPath $LeadsFile)
$now = (Get-Date).ToUniversalTime()

$actionable = @()
foreach ($row in $rows) {
  if (-not $row.repo) { continue }
  if ($row.stage -eq "won" -or $row.stage -eq "lost") { continue }
  if ($row.stage -eq "new") {
    $actionable += $row
    continue
  }
  $due = $false
  if (-not $row.next_action_utc -or "$($row.next_action_utc)".Trim() -eq "") {
    $due = $true
  } else {
    $next = [datetime]::Parse($row.next_action_utc).ToUniversalTime()
    if ($next -le $now) { $due = $true }
  }
  if ($due) { $actionable += $row }
}

$selected = $actionable | Select-Object -First $Limit
if (@($selected).Count -eq 0) {
  Write-Host "No due actions."
  exit 0
}

Write-Host "Due lead actions:"
foreach ($row in $selected) {
  $offer = "$($row.offer_price_usd)"
  if ($offer.Trim() -eq "") { $offer = "10" }
  $source = "$($row.source_channel)"
  if ($source.Trim() -eq "") { $source = "$($row.contact_channel)" }
  Write-Host ("- {0} | stage={1} | source={2} | next={3} | offer=`${4}" -f $row.repo, $row.stage, $source, $row.next_action_utc, $offer)
}
