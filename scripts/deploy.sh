#!/bin/bash
# Script de deployment para Hostgator

set -e

echo "=== Deployment de Tienda Eaciot ==="

# 1. Verificar .env
if [ ! -f .env ]; then
    echo "ERROR: Archivo .env no encontrado"
    echo "Copia .env.example a .env y configura las variables"
    exit 1
fi

# 2. Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt

# 3. Ejecutar migraciones
echo "Ejecutando migraciones..."
alembic upgrade head

# 4. Crear directorio de uploads
echo "Creando directorio de uploads..."
mkdir -p uploads

# 5. Verificar que la app inicia
echo "Verificando que la aplicación inicia..."
python -c "from app.main import app; print('OK')"

echo ""
echo "=== Deployment completado ==="
echo "Visita https://tienda.eaciot.com para verificar"
