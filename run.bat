@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Installez d'abord avec PowerShell : .\scripts\install.ps1
  pause
  exit /b 1
)
.venv\Scripts\python.exe scripts\run.py
pause
