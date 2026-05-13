param(
  [Parameter(Mandatory = $true)]
  [string]$Title,

  [Parameter(Mandatory = $true)]
  [string]$BodyFile,

  [Parameter(Mandatory = $true)]
  [string]$RepoListFile,

  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $BodyFile)) {
  throw "Body file not found: $BodyFile"
}

if (-not (Test-Path -LiteralPath $RepoListFile)) {
  throw "Repo list file not found: $RepoListFile"
}

$repos = @(Get-Content -LiteralPath $RepoListFile |
  ForEach-Object { $_.Trim() } |
  Where-Object { $_ -and -not $_.StartsWith("#") })

if ($repos.Count -eq 0) {
  throw "No repos found in $RepoListFile"
}

if (-not $DryRun) {
  gh auth status | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run gh auth login or set GH_TOKEN."
  }
}

foreach ($repo in $repos) {
  if ($DryRun) {
    Write-Host "[DRY RUN] Would create issue in $repo"
    continue
  }

  try {
    $issueUrl = gh issue create `
      --repo $repo `
      --title $Title `
      --body-file $BodyFile
    if ($LASTEXITCODE -ne 0) {
      throw "gh issue create failed"
    }
    Write-Host "Created: $issueUrl"
  } catch {
    Write-Warning "Failed for ${repo}: $($_.Exception.Message)"
  }
}

Write-Host "Done."
