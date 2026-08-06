# Task 1: Inicializar proyecto Python y dependencias

## Context
- Proyecto: tienda-eaciot (tienda online para tienda.eaciot.com)
- Objetivo: Crear la estructura base del proyecto con dependencias
- Usuario afectado: Desarrolladores del proyecto

## Qué construir
- Crear directorio del proyecto (ya existe en C:\Users\Manu\tienda-eaciot)
- Crear requirements.txt con todas las dependencias
- Crear .env.example con variables de entorno
- Crear .gitignore para Python
- Crear README.md básico

## Archivos a crear
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `README.md`

## Criterios de aceptación
- [ ] requirements.txt contiene todas las dependencias listadas
- [ ] .env.example tiene todas las variables de entorno necesarias
- [ ] .gitignore excluye archivos comunes de Python
- [ ] README.md describe el proyecto brevemente

## Dependencias (requirements.txt)
```
fastapi==0.110.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.29
asyncpg==0.29.0
alembic==1.13.1
auth0-python==4.7.1
python-jose[cryptography]==3.3.0
httpx==0.27.0
ollama==0.1.8
stripe==8.11.0
paypalhttp==1.0.1
jinja2==3.1.3
python-multipart==0.0.9
pydantic[email]==2.6.4
python-dotenv==1.0.1
pytest==8.1.1
pytest-asyncio==0.23.5
```

## Variables de entorno (.env.example)
```
APP_NAME=Tienda Eaciot
APP_SECRET_KEY=change-me-to-random-secret
FRONTEND_URL=https://tienda.eaciot.com
DEBUG=true

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tienda_eaciot

AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_CALLBACK_URL=https://tienda.eaciot.com/auth/callback
AUTH0_AUDIENCE=https://api.eaciot.com

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3

STRIPE_SECRET_KEY=sk_test_your-key
STRIPE_WEBHOOK_SECRET=whsec_your-secret
STRIPE_PUBLISHABLE_KEY=pk_test_your-key

PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_MODE=sandbox

UPLOAD_DIR=./uploads
MAX_FILE_SIZE=104857600
```

## .gitignore
```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env
.eggs/
*.egg-info/
dist/
build/
uploads/
*.db
.pytest_cache/
.mypy_cache/
```

## Restricciones
- No romper: N/A (proyecto nuevo)
- No tocar: N/A
- Preferencias tech: Python 3.11+, FastAPI
- Seguridad / permisos: N/A

## Fuera de alcance
- Configuración de Docker (Task 3)
- Código de aplicación (Tasks 2+)

## Entregables
- 4 archivos creados en C:\Users\Manu\tienda-eaciot\
- Commit con mensaje descriptivo

## Cómo verificar
- Verificar que los archivos existen
- Verificar contenido de cada archivo
- Ejecutar: `pip install -r requirements.txt` (opcional, solo verificar sintaxis)
