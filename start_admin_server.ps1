$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

if (-Not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Error 'Virtual environment not found at .venv\Scripts\python.exe'
    exit 1
}

Write-Host 'Backing up brain.db before starting admin server...'
& .venv\Scripts\python.exe .\backup_brain_db.py

Write-Host 'Starting admin server on port 8001...'
Start-Process -FilePath .venv\Scripts\python.exe -ArgumentList '.\admin_server.py' -WindowStyle Hidden
Write-Host 'Admin server started. Open http://localhost:8001/admin'
