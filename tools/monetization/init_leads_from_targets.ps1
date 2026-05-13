param(
  [string]$TargetFile = "tools/monetization/target_repos.txt",
  [string]$LeadsFile = "tools/monetization/leads_tracker.csv",
  [double]$DefaultOfferUsd = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common_tracker.ps1")

if (-not (Test-Path -LiteralPath $TargetFile)) {
  throw "Target file not found: $TargetFile"
}

Ensure-LeadsTrackerSchema -LeadsFile $LeadsFile

$existingRows = @(Import-Csv -LiteralPath $LeadsFile)
$existing = @{}
foreach ($row in $existingRows) {
  if ($row.repo) { $existing[$row.repo] = $true }
}

$repos = Get-Content -LiteralPath $TargetFile |
  ForEach-Object { $_.Trim() } |
  Where-Object { $_ -and -not $_.StartsWith("#") }

$now = (Get-Date).ToUniversalTime()
$added = 0

foreach ($repo in $repos) {
  if ($existing.ContainsKey($repo)) { continue }
  $parts = $repo.Split("/")
  if ($parts.Count -ne 2) { continue }
  $owner = $parts[0]
  $name = $parts[1]
  $last = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
  $next = $now.AddHours(4).ToString("yyyy-MM-ddTHH:mm:ssZ")
  $line = "$repo,$owner,$name,new,$last,$next,$DefaultOfferUsd,github,github,seeded-from-targets"
  Add-Content -LiteralPath $LeadsFile -Value $line
  $added += 1
}

Write-Host "Added leads: $added"
