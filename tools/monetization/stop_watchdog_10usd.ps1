Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$targets = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -like "*watchdog_10usd.ps1*" })

if (@($targets).Count -eq 0) {
  Write-Host "No watchdog process found."
  exit 0
}

foreach ($p in $targets) {
  Stop-Process -Id $p.ProcessId -Force
  Write-Host "Stopped watchdog PID=$($p.ProcessId)"
}
