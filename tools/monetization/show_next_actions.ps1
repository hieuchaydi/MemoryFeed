param(
  [int]$Limit = 10,
  [string]$LeadsFile = "tools/monetization/leads_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $LeadsFile)) {
  throw "Leads file not found: $LeadsFile"
}

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
  Write-Host ("- {0} | stage={1} | next={2} | offer=`${3}" -f $row.repo, $row.stage, $row.next_action_utc, $row.budget_offer_usd)
}
