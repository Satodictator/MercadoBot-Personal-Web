$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "CONFIGURAR VAULT PRIVADO - MERCADOBOT PERSONAL OS" -ForegroundColor Cyan
Write-Host "Los datos personales se cifran antes de llegar al repositorio publico." -ForegroundColor Yellow

$Candidates = @(
    (Join-Path $env:USERPROFILE "OneDrive\Desktop\MercadoBot-Personal-Web"),
    (Join-Path $env:USERPROFILE "Desktop\MercadoBot-Personal-Web"),
    (Join-Path $env:USERPROFILE "OneDrive\Escritorio\MercadoBot-Personal-Web"),
    (Join-Path $env:USERPROFILE "Escritorio\MercadoBot-Personal-Web"),
    (Get-Location).Path
) | Select-Object -Unique

$Project = $Candidates | Where-Object { Test-Path (Join-Path $_ ".git") } | Select-Object -First 1
if (-not $Project) { throw "No se encontro la carpeta MercadoBot-Personal-Web con su repositorio Git." }
Set-Location $Project
Write-Host "Proyecto: $Project" -ForegroundColor Green

$Python = Join-Path $Project ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Py = Get-Command py -ErrorAction SilentlyContinue
    if ($Py) { $Python = "py" } else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
& $Python -m pip install "cryptography>=44,<48" | Out-Host

$PrivateDir = Join-Path $Project "private"
$VaultDir = Join-Path $Project "vault"
New-Item -ItemType Directory -Force -Path $PrivateDir, $VaultDir | Out-Null
$PersonalJson = Join-Path $PrivateDir "personal.json"
$Template = Join-Path $Project "config\personal_system_template.json"
if (-not (Test-Path $PersonalJson)) {
    Copy-Item $Template $PersonalJson
    Write-Host "Se creo la plantilla privada: $PersonalJson" -ForegroundColor Green
    Write-Host "Puedes editarla antes de volver a ejecutar este script." -ForegroundColor Yellow
}

$KeyFile = Join-Path $PrivateDir ".vault-key"
if (-not (Test-Path $KeyFile)) { & $Python -m app.private_vault generate-key --output $KeyFile }
$Key = (Get-Content $KeyFile -Raw).Trim()
if (-not $Key) { throw "No se pudo generar la clave del vault." }

$Gh = Get-Command gh -ErrorAction Stop
& $Gh.Source auth status | Out-Host
$Key | & $Gh.Source secret set STATE_ENCRYPTION_KEY --body-file - | Out-Host

$Encrypted = Join-Path $VaultDir "personal.enc"
& $Python -m app.private_vault encrypt --input $PersonalJson --output $Encrypted --key-file $KeyFile
Write-Host "Vault cifrado creado: $Encrypted" -ForegroundColor Green

& git config commit.gpgsign false
& git config tag.gpgsign false
& git checkout main | Out-Host
& git pull --ff-only origin main | Out-Host
& git add vault/personal.enc
& git diff --cached --quiet
$HasChanges = $LASTEXITCODE -ne 0
if ($HasChanges) {
    & git commit -m "Actualizar vault personal cifrado" | Out-Host
    & git push origin main | Out-Host
    Write-Host "Vault cifrado publicado. GitHub Actions iniciara una nueva ejecucion." -ForegroundColor Green
} else {
    Write-Host "El vault cifrado no cambio." -ForegroundColor Yellow
}

Write-Host "IMPORTANTE" -ForegroundColor Yellow
Write-Host "- private\personal.json y private\.vault-key permanecen solo en esta PC."
Write-Host "- PUBLISH_PRIVATE_SUMMARY permanece false."
Write-Host "- Las ordenes reales permanecen bloqueadas."
