$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

Write-Host 'Stopping existing admin server processes...'
& .\stop_admin_server.ps1

Write-Host 'Starting admin server with backup...'
& .\start_admin_server.ps1
