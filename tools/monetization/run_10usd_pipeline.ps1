param(
  [double]$GoalUsd = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== 10 USD Pipeline ==="

$statusScript = "tools/monetization/revenue_status.ps1"
$postScript = "tools/monetization/post_partnership_issues.ps1"
$initLeadsScript = "tools/monetization/init_leads_from_targets.ps1"
$nextActionsScript = "tools/monetization/show_next_actions.ps1"
$bodyFile = "tools/monetization/issue_body_partnership.md"
$repoFile = "tools/monetization/target_repos.txt"

if (-not (Test-Path -LiteralPath $statusScript)) { throw "Missing $statusScript" }
if (-not (Test-Path -LiteralPath $postScript)) { throw "Missing $postScript" }
if (-not (Test-Path -LiteralPath $initLeadsScript)) { throw "Missing $initLeadsScript" }
if (-not (Test-Path -LiteralPath $nextActionsScript)) { throw "Missing $nextActionsScript" }

Write-Host ""
Write-Host "[1/5] Current revenue status"
powershell -ExecutionPolicy Bypass -File $statusScript -GoalUsd $GoalUsd

Write-Host ""
Write-Host "[2/5] Initialize leads from target list"
powershell -ExecutionPolicy Bypass -File $initLeadsScript

Write-Host ""
Write-Host "[3/5] Checking GitHub auth"
cmd /c "gh auth status >nul 2>nul"
$authOk = ($LASTEXITCODE -eq 0)

if (-not $authOk) {
  Write-Host "GitHub auth missing. Skipping issue posting. Run: gh auth login"
} else {
  Write-Host ""
  Write-Host "[4/5] Posting partnership issues"
  powershell -ExecutionPolicy Bypass -File $postScript `
    -Title "[Partnership] Scoped integration collaboration" `
    -BodyFile $bodyFile `
    -RepoListFile $repoFile
}

Write-Host ""
Write-Host "[5/5] Due follow-ups"
powershell -ExecutionPolicy Bypass -File $nextActionsScript -Limit 10

Write-Host ""
Write-Host "Pipeline done. Record incoming payments with record_payment.ps1 and update lead stages."
