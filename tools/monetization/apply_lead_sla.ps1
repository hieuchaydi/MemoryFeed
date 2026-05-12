param(
  [string]$LeadsFile = "tools/monetization/leads_tracker.csv",
  [switch]$DirectOnly,
  [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

Ensure-LeadsTrackerSchema -LeadsFile $LeadsFile
$rows = @(Import-Csv -LiteralPath $LeadsFile)
$now = (Get-Date).ToUniversalTime()

function Get-SlaMinutes {
  param([string]$Stage, [string]$SourceChannel)
  $source = "$SourceChannel".ToLower()
  $isDirect = @("facebook","zalo","linkedin","community") -contains $source
  if ($isDirect) {
    if ($Stage -eq "replied") { return 120 }
    if ($Stage -eq "negotiating") { return 480 }
    return 30
  }

  if ($Stage -eq "replied") { return 480 }
  if ($Stage -eq "negotiating") { return 720 }
  if ($Stage -eq "new") { return 240 }
  return 720
}

$updated = 0
foreach ($row in $rows) {
  if (-not $row.repo) { continue }
  if ($row.stage -eq "won" -or $row.stage -eq "lost") { continue }
  $source = "$($row.source_channel)".ToLower()
  $isDirect = @("facebook","zalo","linkedin","community") -contains $source
  if ($DirectOnly -and -not $isDirect) { continue }

  $minutes = Get-SlaMinutes -Stage $row.stage -SourceChannel $row.source_channel
  $target = $now.AddMinutes($minutes).ToString("yyyy-MM-ddTHH:mm:ssZ")

  $shouldUpdate = $Force
  if (-not $shouldUpdate) {
    if (-not $row.next_action_utc -or "$($row.next_action_utc)".Trim() -eq "") {
      $shouldUpdate = $true
    } else {
      $next = [datetime]::Parse($row.next_action_utc).ToUniversalTime()
      if ($next -le $now) { $shouldUpdate = $true }
    }
  }

  if ($shouldUpdate) {
    $row.next_action_utc = $target
    $updated += 1
  }
}

$rows | Export-Csv -LiteralPath $LeadsFile -NoTypeInformation
Write-Host "Applied SLA updates: $updated"
