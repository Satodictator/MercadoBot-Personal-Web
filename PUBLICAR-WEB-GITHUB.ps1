#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$NombreRepositorio = 'MercadoBot-Personal-Web'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

function Paso([string]$Texto) {
    Write-Host "`n==> $Texto" -ForegroundColor Cyan
}

function Probar-Nativo {
    param(
        [Parameter(Mandatory = $true)][string]$Programa,
        [Parameter(Mandatory = $true)][string[]]$Argumentos
    )

    $Anterior = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'SilentlyContinue'
        & $Programa @Argumentos 1>$null 2>$null
        $Codigo = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $Anterior
    }

    return ($Codigo -eq 0)
}

function Ejecutar-Nativo {
    param(
        [Parameter(Mandatory = $true)][string]$Programa,
        [Parameter(Mandatory = $true)][string[]]$Argumentos,
        [Parameter(Mandatory = $true)][string]$MensajeError
    )

    $Anterior = $ErrorActionPreference
    try {
        # Evita que Windows PowerShell 5.1 convierta stderr normal en una excepcion.
        $ErrorActionPreference = 'Continue'
        & $Programa @Argumentos
        $Codigo = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $Anterior
    }

    if ($Codigo -ne 0) {
        throw "$MensajeError Codigo de salida: $Codigo"
    }
}

Paso 'Comprobando Git, GitHub CLI y autenticacion'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Falta Git.'
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'Falta GitHub CLI.'
}

$Autenticado = Probar-Nativo -Programa 'gh' -Argumentos @('auth', 'status')
if (-not $Autenticado) {
    Ejecutar-Nativo -Programa 'gh' -Argumentos @('auth', 'login', '--web', '--git-protocol', 'https') -MensajeError 'No se pudo iniciar sesion en GitHub.'
}

$UsuarioSalida = @(& gh api user --jq '.login')
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo consultar el usuario de GitHub.'
}
$Usuario = (($UsuarioSalida -join '')).Trim()
if ([string]::IsNullOrWhiteSpace($Usuario)) {
    throw 'No se pudo determinar el usuario de GitHub.'
}

$RepoCompleto = "$Usuario/$NombreRepositorio"
$UrlRepo = "https://github.com/$RepoCompleto"
$UrlWeb = "https://$Usuario.github.io/$NombreRepositorio/"

Paso 'Preparando el primer commit local'
if (-not (Test-Path '.git')) {
    Ejecutar-Nativo -Programa 'git' -Argumentos @('init') -MensajeError 'No se pudo iniciar Git.'
}

Ejecutar-Nativo -Programa 'git' -Argumentos @('branch', '-M', 'main') -MensajeError 'No se pudo seleccionar la rama main.'
Ejecutar-Nativo -Programa 'git' -Argumentos @('config', '--local', 'user.name', $Usuario) -MensajeError 'No se pudo configurar el nombre de Git.'
Ejecutar-Nativo -Programa 'git' -Argumentos @('config', '--local', 'user.email', "$Usuario@users.noreply.github.com") -MensajeError 'No se pudo configurar el correo de Git.'
Ejecutar-Nativo -Programa 'git' -Argumentos @('config', '--local', 'commit.gpgsign', 'false') -MensajeError 'No se pudo desactivar GPG para este repositorio.'
Ejecutar-Nativo -Programa 'git' -Argumentos @('config', '--local', 'tag.gpgsign', 'false') -MensajeError 'No se pudo desactivar la firma de etiquetas.'
Ejecutar-Nativo -Programa 'git' -Argumentos @('config', '--local', 'core.autocrlf', 'true') -MensajeError 'No se pudo configurar el formato de lineas.'

Ejecutar-Nativo -Programa 'git' -Argumentos @('add', '--all') -MensajeError 'No se pudieron preparar los archivos.'

# git for-each-ref termina correctamente y devuelve vacio cuando aun no existe main.
$ReferenciaMain = @(& git for-each-ref '--format=%(objectname)' 'refs/heads/main')
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo comprobar la rama main.'
}
$HayCommit = -not [string]::IsNullOrWhiteSpace((($ReferenciaMain -join '')).Trim())

& git diff --cached --quiet
$HayCambios = ($LASTEXITCODE -ne 0)

if ($HayCambios -or -not $HayCommit) {
    Ejecutar-Nativo -Programa 'git' -Argumentos @('commit', '--no-gpg-sign', '-m', 'MercadoBot Web con GitHub Actions y Pages') -MensajeError 'No se pudo crear el primer commit.'
} else {
    Write-Host 'El commit local ya estaba preparado.' -ForegroundColor Green
}

Paso "Creando o actualizando $RepoCompleto"
$Existe = Probar-Nativo -Programa 'gh' -Argumentos @('repo', 'view', $RepoCompleto, '--json', 'name')

if (-not $Existe) {
    Ejecutar-Nativo -Programa 'gh' -Argumentos @(
        'repo', 'create', $RepoCompleto,
        '--public',
        '--description', 'Bot personal de analisis multiactivo con panel web automatico',
        '--source', '.',
        '--remote', 'origin',
        '--push'
    ) -MensajeError 'No se pudo crear y subir el repositorio.'
} else {
    $Remotos = @(& git remote)
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudieron consultar los remotos de Git.'
    }

    if ($Remotos -notcontains 'origin') {
        Ejecutar-Nativo -Programa 'git' -Argumentos @('remote', 'add', 'origin', "$UrlRepo.git") -MensajeError 'No se pudo agregar el remoto origin.'
    } else {
        $OriginSalida = @(& git remote get-url origin)
        if ($LASTEXITCODE -ne 0) {
            throw 'No se pudo consultar el remoto origin.'
        }
        $Origin = (($OriginSalida -join '')).Trim()
        if ($Origin -notmatch [regex]::Escape($RepoCompleto)) {
            Ejecutar-Nativo -Programa 'git' -Argumentos @('remote', 'set-url', 'origin', "$UrlRepo.git") -MensajeError 'No se pudo corregir el remoto origin.'
        }
    }

    Ejecutar-Nativo -Programa 'git' -Argumentos @('push', '-u', 'origin', 'main') -MensajeError 'No se pudo subir la actualizacion a GitHub.'
}

Paso 'Configurando permisos de GitHub Actions'
$PermisosOk = Probar-Nativo -Programa 'gh' -Argumentos @(
    'api', '--method', 'PUT',
    "repos/$RepoCompleto/actions/permissions/workflow",
    '-f', 'default_workflow_permissions=write',
    '-F', 'can_approve_pull_request_reviews=false'
)
if ($PermisosOk) {
    Write-Host 'Permisos de Actions configurados.' -ForegroundColor Green
} else {
    Write-Host 'Aviso: GitHub no permitio cambiar los permisos generales; el workflow contiene sus permisos declarados.' -ForegroundColor Yellow
}

Paso 'Configurando GitHub Pages para Actions'
$PagesExiste = Probar-Nativo -Programa 'gh' -Argumentos @('api', "repos/$RepoCompleto/pages")
if (-not $PagesExiste) {
    $PagesOk = Probar-Nativo -Programa 'gh' -Argumentos @(
        'api', '--method', 'POST', "repos/$RepoCompleto/pages", '-f', 'build_type=workflow'
    )
} else {
    $PagesOk = Probar-Nativo -Programa 'gh' -Argumentos @(
        'api', '--method', 'PUT', "repos/$RepoCompleto/pages", '-f', 'build_type=workflow'
    )
}

if ($PagesOk) {
    Write-Host 'GitHub Pages configurado para publicar mediante Actions.' -ForegroundColor Green
} else {
    Write-Host 'Aviso: Pages se intentara completar durante la primera ejecucion del workflow.' -ForegroundColor Yellow
}

Paso 'Iniciando la primera exploracion en GitHub'
Start-Sleep -Seconds 5
$WorkflowIniciado = Probar-Nativo -Programa 'gh' -Argumentos @('workflow', 'run', 'cloud.yml', '--repo', $RepoCompleto)
if ($WorkflowIniciado) {
    Write-Host 'Primera exploracion solicitada.' -ForegroundColor Green
} else {
    Write-Host 'El push inicial ya debe haber iniciado MercadoBot Web automaticamente.' -ForegroundColor Yellow
}

Write-Host "`nPUBLICACION CONFIGURADA" -ForegroundColor Green
Write-Host "Repositorio: $UrlRepo"
Write-Host "Panel web:  $UrlWeb"
Write-Host 'El bot se ejecutara en GitHub aunque la PC este apagada.' -ForegroundColor Green
Write-Host 'La pagina aparecera cuando termine la primera ejecucion MercadoBot Web en Actions.' -ForegroundColor Yellow

Start-Process $UrlRepo
