$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (Test-Path ".env") {
  Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $parts = $line -split "=", 2
    if ($parts.Count -eq 2) {
      $k = $parts[0].Trim()
      $v = $parts[1].Trim().Trim('"').Trim("'")
      if ($k) {
        [Environment]::SetEnvironmentVariable($k, $v, "Process")
      }
    }
  }
}

Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Cyan
python --version | Out-Null
npm -v | Out-Null

if (-not $env:GEMINI_API_KEY) {
  Write-Host "Missing GEMINI_API_KEY" -ForegroundColor Red
  Write-Host 'Set it first: $env:GEMINI_API_KEY = "your_key"' -ForegroundColor Yellow
  exit 1
}

if (-not $env:GROQ_API_KEY) {
  Write-Host "Missing GROQ_API_KEY" -ForegroundColor Red
  Write-Host 'Set it first: $env:GROQ_API_KEY = "your_key"' -ForegroundColor Yellow
  exit 1
}

Write-Host "[2/5] Installing Python package..." -ForegroundColor Cyan
python -m pip install -e .

Write-Host "[3/5] Installing frontend dependencies..." -ForegroundColor Cyan
Push-Location frontend
npm install
Pop-Location

Write-Host "[4/5] Checking LLM providers..." -ForegroundColor Cyan
memoryfeed models

Write-Host "[5/5] Starting services..." -ForegroundColor Cyan
$backend = Start-Process -FilePath "cmd.exe" -ArgumentList "/c memoryfeed serve" -PassThru -WindowStyle Hidden
$frontend = Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$root\frontend`" && npm run dev -- --host 127.0.0.1 --port 5173" -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "MemoryFeed is running." -ForegroundColor Green
Write-Host "- Frontend: http://localhost:5173"
Write-Host "- Backend : http://localhost:7749"
Write-Host ""
Write-Host "Backend PID : $($backend.Id)"
Write-Host "Frontend PID: $($frontend.Id)"
Write-Host ""
Write-Host "To stop:" -ForegroundColor Yellow
Write-Host "Stop-Process -Id $($backend.Id),$($frontend.Id)"
