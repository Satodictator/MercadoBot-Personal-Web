Write-Host 'Esta versión se publica como panel web permanente.' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'PUBLICAR-WEB-GITHUB.ps1')
