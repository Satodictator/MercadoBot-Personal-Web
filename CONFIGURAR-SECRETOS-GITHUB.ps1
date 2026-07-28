#requires -Version 5.1
[CmdletBinding()]
param([string]$NombreRepositorio = 'MercadoBot-Personal-Web')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Falta GitHub CLI.' }
& gh auth status
$Usuario = (& gh api user --jq '.login').Trim()
$Repo = "$Usuario/$NombreRepositorio"

function Guardar-Secreto([string]$Nombre, [string]$Descripcion) {
    $Valor = Read-Host "$Descripcion (Enter para omitir)"
    if ($Valor) {
        $Valor | & gh secret set $Nombre --repo $Repo
        if ($LASTEXITCODE -ne 0) { throw "No se pudo guardar $Nombre" }
        Write-Host "$Nombre guardado de forma secreta en GitHub." -ForegroundColor Green
    }
}

Guardar-Secreto 'TELEGRAM_BOT_TOKEN' 'Token del bot de Telegram'
Guardar-Secreto 'TELEGRAM_CHAT_ID' 'Identificador del chat de Telegram'
Guardar-Secreto 'DISCORD_WEBHOOK_URL' 'Webhook de Discord'
Guardar-Secreto 'ALPACA_API_KEY' 'Clave de Alpaca'
Guardar-Secreto 'ALPACA_SECRET_KEY' 'Secreto de Alpaca'
Guardar-Secreto 'ALPACA_DATA_FEED' 'Feed de Alpaca, por ejemplo iex'
Write-Host 'Configuración terminada. Ningún secreto fue escrito dentro del repositorio.' -ForegroundColor Green
