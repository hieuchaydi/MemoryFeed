Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$targets = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -like "*continuous_until_10usd.ps1*" })

if (-not $targets -or @($targets).Count -eq 0) {
  Write-Host "No continuous loop process found."
  exit 0
}

foreach ($p in $targets) {
  Stop-Process -Id $p.ProcessId -Force
  Write-Host "Stopped PID=$($p.ProcessId)"
}
