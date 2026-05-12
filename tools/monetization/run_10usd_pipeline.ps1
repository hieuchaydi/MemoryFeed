param(
  [double]$GoalUsd = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== 10 USD Pipeline ==="

$statusScript = "tools/monetization/revenue_status.ps1"
$postScript = "tools/monetization/post_partnership_issues.ps1"
$bodyFile = "tools/monetization/issue_body_partnership.md"
$repoFile = "tools/monetization/target_repos.txt"

if (-not (Test-Path -LiteralPath $statusScript)) { throw "Missing $statusScript" }
if (-not (Test-Path -LiteralPath $postScript)) { throw "Missing $postScript" }

Write-Host ""
Write-Host "[1/3] Current revenue status"
powershell -ExecutionPolicy Bypass -File $statusScript -GoalUsd $GoalUsd

Write-Host ""
Write-Host "[2/3] Checking GitHub auth"
gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "GitHub auth missing. Run: gh auth login"
  exit 1
}

Write-Host ""
Write-Host "[3/3] Posting partnership issues"
powershell -ExecutionPolicy Bypass -File $postScript `
  -Title "[Partnership] Scoped integration collaboration" `
  -BodyFile $bodyFile `
  -RepoListFile $repoFile

Write-Host ""
Write-Host "Pipeline done. Record incoming payments with record_payment.ps1."
