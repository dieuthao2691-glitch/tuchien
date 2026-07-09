$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

if (-Not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Error 'Virtual environment not found at .venv\Scripts\python.exe'
    exit 1
}

Write-Host 'Ensuring admin DB schema exists...'
& .venv\Scripts\python.exe .\admin_server.py
