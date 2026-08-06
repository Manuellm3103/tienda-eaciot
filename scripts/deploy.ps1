# Script de deployment para Windows

Write-Host "=== Deployment de Tienda Eaciot ===" -ForegroundColor Cyan

# 1. Verificar .env
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: Archivo .env no encontrado" -ForegroundColor Red
    Write-Host "Copia .env.example a .env y configura las variables"
    exit 1
}

# 2. Instalar dependencias
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
pip install -r requirements.txt

# 3. Ejecutar migraciones
Write-Host "Ejecutando migraciones..." -ForegroundColor Yellow
alembic upgrade head

# 4. Crear directorio de uploads
Write-Host "Creando directorio de uploads..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "uploads" -Force

# 5. Verificar que la app inicia
Write-Host "Verificando que la aplicación inicia..." -ForegroundColor Yellow
python -c "from app.main import app; print('OK')"

Write-Host ""
Write-Host "=== Deployment completado ===" -ForegroundColor Green
Write-Host "Visita https://tienda.eaciot.com para verificar"
