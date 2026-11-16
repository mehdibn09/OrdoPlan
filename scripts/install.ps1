$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host 'Installation terminée. Lancez : .\.venv\Scripts\python.exe scripts\run.py'
