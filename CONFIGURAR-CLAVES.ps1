$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
Start-Process notepad.exe (Resolve-Path ".env")
Write-Host "Agrega únicamente tus claves privadas en .env. Ese archivo está excluido de Git." -ForegroundColor Yellow
