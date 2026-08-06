# Guía de Deployment - tienda.eaciot.com

## Requisitos del Servidor

- **Hosting:** Hostgator (plan con soporte Python)
- **Dominio:** eaciot.com (subdominio: tienda.eaciot.com)
- **Python:** 3.11+
- **PostgreSQL:** 15+ (puede ser externo como Supabase, Neon, o RDS)
- **Ollama:** Puede correr localmente o en servidor separado

---

## Opción 1: Hostgator con Python (Recomendado)

### Paso 1: Preparar el proyecto

```bash
# 1. Crear archivo de requirements para producción
cd C:\Users\Manu\tienda-eaciot

# 2. Crear archivo .htaccess para Apache
# 3. Crear archivo passenger_wsgi.py
# 4. Crear script de inicio
```

### Paso 2: Configurar PostgreSQL externo

Hostgator no incluye PostgreSQL. Usar servicio externo:

**Opción A: Supabase (Gratis)**
1. Ir a https://supabase.com
2. Crear proyecto
3. Obtener connection string
4. Actualizar DATABASE_URL en .env

**Opción B: Neon (Gratis)**
1. Ir a https://neon.tech
2. Crear proyecto
3. Obtener connection string
4. Actualizar DATABASE_URL en .env

**Opción C: Railway (Pago)**
1. Ir a https://railway.app
2. Crear proyecto PostgreSQL
3. Obtener connection string

### Paso 3: Subir archivos a Hostgator

```bash
# Via FTP o File Manager de cPanel
# Subir todos los archivos a: public_html/tienda/
```

### Paso 4: Configurar Python en cPanel

1. Ir a **Setup Python App** en cPanel
2. Crear aplicación:
   - Python version: 3.11
   - Application root: `/home/usuario/public_html/tienda`
   - Application URL: `tienda.eaciot.com`
   - Application startup file: `passenger_wsgi.py`

### Paso 5: Instalar dependencias

```bash
# En Terminal de cPanel o SSH
cd /home/usuario/public_html/tienda
source /home/usuario/virtualenv/public_html/tienda/3.11/bin/activate
pip install -r requirements.txt
```

### Paso 6: Configurar variables de entorno

Crear archivo `.env` en el servidor:

```env
APP_NAME=Tienda Eaciot
APP_SECRET_KEY=tu-clave-secreta-muy-larga-y-segura
FRONTEND_URL=https://tienda.eaciot.com
DEBUG=false

DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/tienda_eaciot

# SMTP (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=noreply@eaciot.com

# OAuth
GOOGLE_CLIENT_ID=tu-client-id
GOOGLE_CLIENT_SECRET=tu-client-secret
# ... demás OAuth

# Pagos
STRIPE_SECRET_KEY=tu-stripe-key
STRIPE_WEBHOOK_SECRET=tu-webhook-secret
```

### Paso 7: Ejecutar migraciones

```bash
cd /home/usuario/public_html/tienda
source /home/usuario/virtualenv/public_html/tienda/3.11/bin/activate
alembic upgrade head
```

### Paso 8: Configurar dominio

1. Ir a **Subdomains** en cPanel
2. Crear subdominio: `tienda.eaciot.com`
3. Apuntar a: `/home/usuario/public_html/tienda`

---

## Opción 2: Docker en VPS (DigitalOcean, Hetzner)

### Paso 1: Crear servidor VPS

```bash
# DigitalOcean Droplet o Hetzner VPS
# Ubuntu 22.04, 2GB RAM mínimo
```

### Paso 2: Instalar Docker

```bash
# En el servidor
apt update && apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install docker-compose -y
```

### Paso 3: Subir proyecto

```bash
# Desde tu máquina local
scp -r C:\Users\Manu\tienda-eaciot root@tu-ip:/opt/tienda-eaciot
```

### Paso 4: Configurar .env en servidor

```bash
# En el servidor
cd /opt/tienda-eaciot
nano .env
# Configurar todas las variables
```

### Paso 5: Iniciar servicios

```bash
cd /opt/tienda-eaciot
docker-compose -f docker-compose.prod.yml up -d
```

### Paso 6: Configurar Nginx reverse proxy

```nginx
# /etc/nginx/sites-available/tienda.eaciot.com
server {
    listen 80;
    server_name tienda.eaciot.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Paso 7: Configurar SSL con Let's Encrypt

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d tienda.eaciot.com
```

---

## Opción 3: Railway (Más fácil)

### Paso 1: Crear cuenta en Railway

1. Ir a https://railway.app
2. Conectar GitHub

### Paso 2: Crear proyecto

1. New Project → Deploy from GitHub
2. Seleccionar repositorio
3. Agregar PostgreSQL

### Paso 3: Configurar variables

En Railway → Variables:
- Agregar todas las variables de .env
- DATABASE_URL se auto-configura

### Paso 4: Deploy

Railway hace deploy automático en cada push a main.

### Paso 5: Configurar dominio

1. Settings → Domains
2. Agregar: tienda.eaciot.com
3. Configurar DNS CNAME

---

## Archivos de Producción

### passenger_wsgi.py (Hostgator)

```python
import sys
import os

# Agregar directorio del proyecto al path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app

# Passenger necesita esta variable
application = app
```

### .htaccess (Hostgator)

```apache
PassengerAppRoot /home/usuario/public_html/tienda
PassengerBaseURI /
PassengerPython /home/usuario/virtualenv/public_html/tienda/3.11/bin/python

RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

### docker-compose.prod.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: always

volumes:
  ollama_data:
```

---

## Checklist de Deployment

### Antes de deployar

- [ ] Configurar PostgreSQL externo (Supabase/Neon)
- [ ] Configurar SMTP (Gmail App Password)
- [ ] Configurar OAuth (Google, Microsoft, GitHub)
- [ ] Configurar Stripe/PayPal
- [ ] Generar APP_SECRET_KEY aleatoria
- [ ] Crear .env con todas las variables

### Después de deployar

- [ ] Ejecutar migraciones: `alembic upgrade head`
- [ ] Verificar health: `https://tienda.eaciot.com/health`
- [ ] Probar registro de usuario
- [ ] Probar login con OAuth
- [ ] Probar verificación de email
- [ ] Configurar webhooks de Stripe/PayPal
- [ ] Configurar DNS para tienda.eaciot.com

---

## Comandos Útiles

```bash
# Ver logs
docker-compose logs -f app

# Reiniciar aplicación
docker-compose restart app

# Ejecutar migraciones
docker-compose exec app alembic upgrade head

# Crear usuario admin
docker-compose exec app python -c "
from app.database import async_session
from app.models.user import User
from app.services.auth_service import get_password_hash
import asyncio

async def create_admin():
    async with async_session() as db:
        admin = User(
            email='admin@eaciot.com',
            hashed_password=get_password_hash('tu-password'),
            name='Admin',
            is_admin=True,
            email_verified=True,
        )
        db.add(admin)
        await db.commit()

asyncio.run(create_admin())
"
```

---

## Troubleshooting

### Error: Module not found
```bash
pip install -r requirements.txt
```

### Error: Database connection
Verificar DATABASE_URL y que PostgreSQL acepte conexiones externas.

### Error: SMTP
Verificar credenciales y que "Less secure apps" esté habilitado (Gmail).

### Error: OAuth redirect_uri_mismatch
Verificar que las redirect URIs coincidan exactamente en los proveedores.

---

## Soporte

- Hostgator: https://www.hostgator.com/help
- Supabase: https://supabase.com/docs
- Railway: https://docs.railway.app
