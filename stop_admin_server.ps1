$ErrorActionPreference = 'Stop'
$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine -match 'admin_server\.py'
}

if (-not $processes) {
    Write-Host 'No admin_server.py process found.'
    exit 0
}

$processes | ForEach-Object {
    Write-Host "Stopping process ID: $($_.ProcessId) CommandLine: $($_.CommandLine)"
    Stop-Process -Id $_.ProcessId -Force
}
Write-Host 'Stopped admin_server.py processes.'
