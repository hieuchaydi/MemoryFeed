$ErrorActionPreference = "Stop"

param(
  [string]$HostIp = "0.0.0.0",
  [int]$Port = 7749
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "[1/3] Checking prerequisites..." -ForegroundColor Cyan
python --version | Out-Null
npm -v | Out-Null

Write-Host "[2/3] Installing backend package..." -ForegroundColor Cyan
python -m pip install -e .

Write-Host "[3/3] Building and serving React+Vite web..." -ForegroundColor Cyan
Write-Host "Host: $HostIp"
Write-Host "Port: $Port"
Write-Host "Open: http://<your-server-ip>:$Port"

memoryfeed serve-web --host $HostIp --port $Port
