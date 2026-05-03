$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Cyan
python --version | Out-Null
npm -v | Out-Null
ollama --version | Out-Null

Write-Host "[2/6] Checking Ollama server..." -ForegroundColor Cyan
try {
  Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get | Out-Null
} catch {
  Write-Host "Ollama server is not reachable at http://localhost:11434" -ForegroundColor Red
  Write-Host "Start it first with: ollama serve" -ForegroundColor Yellow
  exit 1
}

Write-Host "[3/6] Installing Python package..." -ForegroundColor Cyan
python -m pip install -e .

Write-Host "[4/6] Installing frontend dependencies..." -ForegroundColor Cyan
Push-Location frontend
npm install
Pop-Location

Write-Host "[5/6] Ensuring local models..." -ForegroundColor Cyan
ollama pull qwen2.5:7b
ollama pull llava:7b

Write-Host "[6/6] Starting services..." -ForegroundColor Cyan
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
