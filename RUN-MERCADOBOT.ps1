$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "No existe el entorno virtual. Ejecuta primero CREAR-MERCADOBOT-PERSONAL.ps1" }
Start-Process "http://127.0.0.1:8000"
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
