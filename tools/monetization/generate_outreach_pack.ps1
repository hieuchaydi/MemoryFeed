param(
  [Parameter(Mandatory = $true)]
  [string]$RepoListFile,

  [Parameter(Mandatory = $true)]
  [string]$OutputFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $RepoListFile)) {
  throw "Repo list file not found: $RepoListFile"
}

$repos = Get-Content -LiteralPath $RepoListFile |
  ForEach-Object { $_.Trim() } |
  Where-Object { $_ -and -not $_.StartsWith("#") }

if ($repos.Count -eq 0) {
  throw "No repos found in $RepoListFile"
}

$lines = @()
$lines += "# Outreach Pack"
$lines += ""
$lines += "Use these ready messages for partnership outreach."
$lines += ""

foreach ($repo in $repos) {
  $name = $repo.Split("/")[-1]
  $lines += "## Target: $repo"
  $lines += ""
  $lines += '```text'
  $lines += "Hi maintainers of $name,"
  $lines += ""
  $lines += "I maintain MemoryFeed (local-first memory + MCP)."
  $lines += "I can contribute a small paid integration scope for $name with a clean PR:"
  $lines += "- focused implementation"
  $lines += "- tests + docs"
  $lines += "- same-day to 72h delivery"
  $lines += ""
  $lines += "Pilot scope starts at `$5 for triage or `$25 for implementation prep."
  $lines += "Repo: https://github.com/hieuchaydi/MemoryFeed"
  $lines += '```'
  $lines += ""
}

Set-Content -LiteralPath $OutputFile -Value $lines -Encoding UTF8
Write-Host "Generated: $OutputFile"
