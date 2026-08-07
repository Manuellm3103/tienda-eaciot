# Deployment con $0 Mensuales - cPanel Hostgator

**Costo total: $0/mes** (solo pagas el hosting que ya tienes)

---

## 🎯 Estrategia: Hybrid Self-Hosted + Free Tier Services

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARQUITECTURA $0/MES                          │
├─────────────────────────────────────────────────────────────────┤
│  cPanel Hostgator (YA LO TIENES)                                │
│  ├── Python App (via Passenger)                                 │
│  ├── SQLite o PostgreSQL externo (gratis)                       │
│  ├── Static files                                               │
│  └── Cron jobs                                                  │
├─────────────────────────────────────────────────────────────────┤
│  SERVICIOS GRATUITOS EXTERNOS                                   │
│  ├── Supabase: PostgreSQL + Auth + Storage (gratis)             │
│  ├── Upstash: Redis (gratis 10k cmds/día)                       │
│  ├── SendGrid: Email transaccional (100/día gratis)             │
│  ├── Sentry: Error tracking (gratis)                            │
│  ├── Cloudflare: CDN + DNS + SSL (gratis)                       │
│  ├── UptimeRobot: Monitoreo (gratis)                            │
│  └── Backblaze B2: Storage (10GB gratis)                        │
├─────────────────────────────────────────────────────────────────┤
│  COSTO: $0/MES                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 SERVICIOS GRATUITOS RECOMENDADOS

### 1. Base de Datos: Supabase (PostgreSQL)

| Característica | Límite Gratis |
|----------------|---------------|
| Storage | 500MB |
| Ancho de banda | 2GB |
| Proyectos | 2 |
| Backups | Automáticos |

**Setup:**
1. Ir a https://supabase.com
2. Crear cuenta (GitHub login)
3. Crear proyecto "tienda-eaciot"
4. Copiar connection string
5. Agregar a .env: `DATABASE_URL=postgresql+asyncpg://...`

---

### 2. Cache/Sessions: Upstash (Redis)

| Característica | Límite Gratis |
|----------------|---------------|
| Commands | 10,000/día |
| Storage | 256MB |
| Conexiones | 100 simultáneas |

**Setup:**
1. Ir a https://upstash.com
2. Crear cuenta
3. Crear Redis database
4. Copiar URL
5. Agregar a .env: `REDIS_URL=...`

---

### 3. Email: SendGrid

| Característica | Límite Gratis |
|----------------|---------------|
| Emails | 100/día |
| Contactos | 2,000 |
| Templates | Sí |

**Setup:**
1. Ir a https://sendgrid.com
2. Crear cuenta
3. Verificar dominio o email
4. Crear API key
5. Agregar a .env: `SENDGRID_API_KEY=...`

**Alternativas:**
- Mailgun: 5,000 emails/mes gratis
- Resend: 3,000 emails/mes gratis
- Amazon SES: $0.10/1000 emails

---

### 4. Error Tracking: Sentry

| Característica | Límite Gratis |
|----------------|---------------|
| Errors | 5,000/mes |
| Performance | 10,000 traces/mes |
| Projects | 1 |
| Retention | 30 días |

**Setup:**
1. Ir a https://sentry.io
2. Crear cuenta
3. Crear proyecto Python
4. Copiar DSN
5. Agregar a .env: `SENTRY_DSN=...`

---

### 5. CDN + DNS + SSL: Cloudflare

| Característica | Límite Gratis |
|----------------|---------------|
| Ancho de banda | Ilimitado |
| SSL | Ilimitado |
| DNS | Ilimitado |
| DDoS protection | Sí |
| Workers | 100k requests/día |

**Setup:**
1. Ir a https://cloudflare.com
2. Crear cuenta
3. Agregar dominio eaciot.com
4. Cambiar nameservers en Hostgator
5. Configurar reglas de cache

---

### 6. Monitoreo: UptimeRobot

| Característica | Límite Gratis |
|----------------|---------------|
| Monitors | 50 |
| Intervalo | 5 minutos |
| Alertas | Email, SMS, Slack |

**Setup:**
1. Ir a https://uptimerobot.com
2. Crear cuenta
3. Agregar monitor: https://tienda.eaciot.com/health
4. Configurar alertas

---

### 7. Storage: Cloudflare R2

| Característica | Límite Gratis |
|----------------|---------------|
| Storage | 10GB |
| Clase A ops | 1M/mes |
| Clase B ops | 10M/mes |
| Egress | Gratis |

**Setup:**
1. Ir a Cloudflare Dashboard
2. R2 Object Storage
3. Crear bucket "tienda-eaciot"
4. Crear API token
5. Agregar a .env

---

### 8. Búsqueda: SQLite FTS (en cPanel)

No necesitas servicio externo. SQLite tiene Full-Text Search integrado.

**Ventajas:**
- $0
- Sin dependencia externa
- Rápido para <100k productos
- Funciona en cPanel

---

## 🔧 CONFIGURACIÓN EN CPANEL

### Paso 1: Verificar soporte Python

1. Login a cPanel
2. Buscar "Setup Python App" o "Python"
3. Si no está disponible, contactar soporte Hostgator

**Si Python NO está disponible:**
Usar opción alternativa con PHP + API

### Paso 2: Crear aplicación Python

1. En cPanel → Setup Python App
2. Configurar:
   - Python version: 3.11
   - Application root: `/home/USER/tienda`
   - Application URL: `tienda.eaciot.com`
   - Startup file: `passenger_wsgi.py`

### Paso 3: Subir archivos

**Opción A: File Manager**
1. cPanel → File Manager
2. Navegar a `/home/USER/tienda`
3. Subir archivos ZIP
4. Descomprimir

**Opción B: Git**
1. cPanel → Git Version Control
2. Clone desde GitHub
3. Auto-deploy en push

**Opción C: SSH (si disponible)**
```bash
ssh user@eaciot.com
cd ~/tienda
git clone https://github.com/tu-repo/tienda-eaciot.git .
pip install -r requirements.txt
```

### Paso 4: Configurar .htaccess

```apache
# Forzar HTTPS
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# Passenger
PassengerAppRoot /home/USER/tienda
PassengerBaseURI /
PassengerPython /home/USER/virtualenv/tienda/3.11/bin/python

# Cache static files
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType image/jpg "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType text/css "access plus 1 month"
    ExpiresByType application/javascript "access plus 1 month"
</IfModule>

# Security headers
<IfModule mod_headers.c>
    Header set X-Content-Type-Options "nosniff"
    Header set X-Frame-Options "SAMEORIGIN"
    Header set X-XSS-Protection "1; mode=block"
    Header set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>
```

### Paso 5: Configurar Cron Jobs

En cPanel → Cron Jobs:

```bash
# Cada 5 minutos: procesar cola de emails
*/5 * * * * cd /home/USER/tienda && /home/USER/virtualenv/tienda/3.11/bin/python scripts/process_emails.py

# Cada hora: actualizar métricas
0 * * * * cd /home/USER/tienda && /home/USER/virtualenv/tienda/3.11/bin/python scripts/update_metrics.py

# Diario: backups
0 2 * * * cd /home/USER/tienda && /home/USER/virtualenv/tienda/3.11/bin/python scripts/backup_db.py

# Diario: limpiar sesiones expiradas
0 3 * * * cd /home/USER/tienda && /home/USER/virtualenv/tienda/3.11/bin/python scripts/cleanup_sessions.py
```

---

## 📋 CHECKLIST DE SETUP GRATUITO

### Servicios Externos (30 min)

- [ ] Crear cuenta Supabase + proyecto
- [ ] Crear cuenta Upstash + Redis
- [ ] Crear cuenta SendGrid + API key
- [ ] Crear cuenta Sentry + proyecto
- [ ] Crear cuenta Cloudflare + dominio
- [ ] Crear cuenta UptimeRobot + monitor

### cPanel (1 hora)

- [ ] Verificar soporte Python
- [ ] Crear aplicación Python
- [ ] Subir archivos
- [ ] Configurar .htaccess
- [ ] Configurar cron jobs
- [ ] Configurar SSL (Cloudflare)

### Configuración (30 min)

- [ ] Crear .env con todas las credenciales
- [ ] Ejecutar migraciones
- [ ] Crear usuario admin
- [ ] Probar health check
- [ ] Probar registro/login
- [ ] Probar envío de email

---

## 🔄 ALTERNATIVA: SQLite (Sin PostgreSQL)

Si no quieres usar Supabase, puedes usar SQLite:

**Ventajas:**
- Sin dependencia externa
- $0 total
- Backups simples (copiar archivo)
- Perfecto para <10k productos

**Desventajas:**
- No soporta concurrencia alta
- No soporta replication
- Más lento para queries complejas

**Cambios necesarios:**

```python
# app/config.py
database_url: str = "sqlite+aiosqlite:///./tienda.db"

# requirements.txt (agregar)
aiosqlite==0.20.0
```

---

## 📊 COMPARATIVA DE COSTOS

| Servicio | Gratis | Pago | Recomendación |
|----------|--------|------|---------------|
| Database | Supabase/Neon | $7-25/mes | Gratis OK |
| Redis | Upstash | $10/mes | Gratis OK |
| Email | SendGrid | $15/mes | Gratis OK |
| Monitoring | Sentry | $26/mes | Gratis OK |
| CDN | Cloudflare | $20/mes | Gratis OK |
| Storage | R2/B2 | $5/mes | Gratis OK |
| Search | SQLite FTS | $30/mes | Gratis OK |
| **TOTAL** | **$0** | **$123+/mes** | **$0** |

---

## ⚠️ LÍMITES DEL PLAN GRATUITO

| Servicio | Límite | Workaround |
|----------|--------|------------|
| Supabase | 500MB DB | Migrar a Neon si crece |
| Upstash | 10k cmds/día | Usar solo para cache crítico |
| SendGrid | 100 emails/día | Cola con reintentos |
| Sentry | 5k errors/mes | Filtrar errors no críticos |
| R2 | 10GB storage | Comprimir imágenes |

---

## 🚀 SCRIPT DE SETUP AUTOMÁTICO

```bash
#!/bin/bash
# scripts/setup_free.sh

echo "=== Setup Tienda Eaciot - $0/mes ==="

# 1. Verificar Python
python3 --version || echo "ERROR: Python no encontrado"

# 2. Crear .env
cat > .env << 'EOF'
APP_NAME=Tienda Eaciot
APP_SECRET_KEY=$(openssl rand -hex 32)
FRONTEND_URL=https://tienda.eaciot.com
DEBUG=false

# Database (Supabase)
DATABASE_URL=postgresql+asyncpg://xxx:xxx@xxx.supabase.co:5432/postgres

# Ollama (opcional - puede correr localmente)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3

# Email (SendGrid)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxx
SMTP_FROM=noreply@eaciot.com

# Sentry
SENTRY_DSN=https://xxx@sentry.io/xxx

# Redis (Upstash)
REDIS_URL=redis://xxx:xxx@xxx.upstash.io:xxx
EOF

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar migraciones
alembic upgrade head

# 5. Crear admin
python scripts/create_admin.py admin@eaciot.com changeme

echo "=== Setup completado ==="
echo "Visita https://tienda.eaciot.com"
```

---

## 📚 RECURSOS

### GitHub Repos Útiles

- [FastAPI + Supabase](https://github.com/supabase/supabase/tree/master/examples/python)
- [SendGrid Python](https.com/github.com/sendgrid/sendgrid-python)
- [Sentry Python](https://github.com/getsentry/sentry-python)
- [Upstash Redis](https://github.com/upstash/upstash-redis-python)

### Documentación

- [Supabase Docs](https://supabase.com/docs)
- [SendGrid Docs](https://docs.sendgrid.com)
- [Cloudflare Docs](https://developers.cloudflare.com)
- [Hostgator Python](https://www.hostgator.com/help/article/python-2)

---

## ✅ VENTAJAS DE ESTE ENFOQUE

1. **$0 mensuales** - Solo pagas hosting existente
2. **Escalable** - Servicios crecen contigo
3. **Confiable** - Backups automáticos
4. **Rápido** - CDN global (Cloudflare)
5. **Seguro** - SSL automático, DDoS protection
6. **Monitoreo** - Alertas 24/7

---

## ⚠️ RIESGOS Y MITIGACIONES

| Riesgo | Mitigación |
|--------|------------|
| Supabase downtime | Backup diario + restore manual |
| SendGrid rate limit | Cola de emails + reintentos |
| cPanel limits | Optimizar queries + cache |
| Storage limit | Comprimir + CDN cache |

---

**¿Quieres que implemente la configuración para algún servicio específico?**
