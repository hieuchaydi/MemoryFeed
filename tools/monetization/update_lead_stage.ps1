param(
  [Parameter(Mandatory = $true)]
  [string]$Repo,

  [Parameter(Mandatory = $true)]
  [ValidateSet("new","contacted","replied","negotiating","won","lost")]
  [string]$Stage,

  [string]$Note = "",
  [int]$NextActionHours = 24,
  [string]$LeadsFile = "tools/monetization/leads_tracker.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $LeadsFile)) {
  throw "Leads file not found: $LeadsFile"
}

$rows = @(Import-Csv -LiteralPath $LeadsFile)
$found = $false
$now = (Get-Date).ToUniversalTime()
$nowUtc = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
$nextUtc = $now.AddHours($NextActionHours).ToString("yyyy-MM-ddTHH:mm:ssZ")
$safeNote = $Note.Replace("`r", " ").Replace("`n", " ").Replace(",", ";")

foreach ($row in $rows) {
  if ($row.repo -eq $Repo) {
    $row.stage = $Stage
    $row.last_action_utc = $nowUtc
    if ($Stage -eq "won" -or $Stage -eq "lost") {
      $row.next_action_utc = ""
    } else {
      $row.next_action_utc = $nextUtc
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
