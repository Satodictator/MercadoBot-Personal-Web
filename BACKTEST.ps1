param([string[]]$Simbolos = @("SPY", "QQQ", "BTC-USD", "ETH-USD", "GC=F"))
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python -m app.backtest @Simbolos
