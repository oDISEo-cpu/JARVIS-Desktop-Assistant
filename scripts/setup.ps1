#Requires -Version 5.1
<#
.SYNOPSIS
    Configura el entorno de JARVIS en Windows.
.DESCRIPTION
    Crea venv, instala dependencias y copia .env.example a .env si no existe.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== JARVIS Setup ===" -ForegroundColor Cyan
Write-Host "Directorio: $ProjectRoot"

# Verificar Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python no encontrado. Instale Python 3.11+ desde https://python.org"
}

$version = python --version 2>&1
Write-Host "Python detectado: $version"

# Crear venv
if (-not (Test-Path ".venv")) {
    Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "Entorno virtual ya existe." -ForegroundColor Green
}

# Activar venv
$activate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
. $activate

# Actualizar pip
Write-Host "Actualizando pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip -q

# Instalar dependencias principales
Write-Host "Instalando dependencias (modo texto)..." -ForegroundColor Yellow
pip install -r requirements.txt

# Copiar .env si no existe
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env creado desde .env.example — configure su API key." -ForegroundColor Yellow
} else {
    Write-Host ".env ya existe, no se sobrescribió." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Setup completado ===" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Cyan
Write-Host "  1. Edite .env con su API key (o configure Ollama para uso gratis)"
Write-Host "  2. Modo texto:  python main.py"
Write-Host "  3. Dry-run:     python main.py --dry-run"
Write-Host "  4. Chat web:    python main.py --web"
Write-Host "  5. Voz (opc.):  pip install -r requirements-voice.txt"
Write-Host "                  python main.py --input-mode voice"
Write-Host ""
