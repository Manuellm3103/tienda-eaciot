# Setup de Servicios Gratuitos - Guía Paso a Paso

## 1. Supabase (PostgreSQL) - 5 minutos

### Crear cuenta y proyecto

1. Ir a https://supabase.com
2. Click "Start your project"
3. Login con GitHub
4. Click "New Project"
5. Llenar:
   - Name: `tienda-eaciot`
   - Database Password: (generar contraseña segura)
   - Region: `East US (North Virginia)`
6. Click "Create new project"
7. Esperar ~2 minutos

### Obtener connection string

1. Ir a Project Settings → Database
2. En "Connection string" → "URI"
3. Copiar algo como:
   ```
   postgresql://postgres.xxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
4. Cambiar `postgresql://` por `postgresql+asyncpg://`
5. Agregar a `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres.xxx:tu-password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

---

## 2. SendGrid (Email) - 10 minutos

### Crear cuenta

1. Ir a https://sendgrid.com
2. Click "Start for Free"
3. Llenar registro
4. Verificar email

### Crear API Key

1. Ir a Settings → API Keys
2. Click "Create API Key"
3. Name: `tienda-eaciot`
4. Permissions: "Full Access"
5. Click "Create & View"
6. **COPIAR LA KEY AHORA** (no se puede ver después)

### Verificar remitente

1. Ir a Settings → Sender Authentication
2. Click "Verify a Single Sender"
3. Llenar con tu email
4. Verificar email recibido

### Configurar .env

```
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxxxx  # Tu API key
SMTP_FROM=tu-email-verificado@tudominio.com
```

---

## 3. Sentry (Error Tracking) - 5 minutos

### Crear cuenta

1. Ir a https://sentry.io
2. Click "Get Started"
3. Login con GitHub
4. Crear organización: `eaciot`

### Crear proyecto

1. Click "Create Project"
2. Platform: "Python"
3. Name: `tienda-eaciot`
4. Alert frequency: "On every new issue"
5. Click "Create Project"
6. Copiar DSN:
   ```
   https://xxxx@xxxx.ingest.sentry.io/xxxx
   ```

### Configurar .env

```
SENTRY_DSN=https://xxxx@xxxx.ingest.sentry.io/xxxx
```

---

## 4. Upstash (Redis) - 5 minutos

### Crear cuenta

1. Ir a https://upstash.com
2. Click "Get Started"
3. Login con GitHub

### Crear Redis database

1. Click "Create Database"
2. Name: `tienda-eaciot`
3. Region: `us-east-1`
4. Click "Create"

### Obtener URL

1. En la página del database, buscar "REST API"
2. Copiar `UPSTASH_REDIS_REST_URL`
3. Formato: `https://xxx.upstash.io`

### Configurar .env

```
REDIS_URL=redis://default:xxx@xxx.upstash.io:xxx
```

---

## 5. Cloudflare (CDN + SSL) - 15 minutos

### Crear cuenta

1. Ir a https://cloudflare.com
2. Click "Sign Up"
3. Crear cuenta

### Agregar dominio

1. Click "Add a Site"
2. Ingresar: `eaciot.com`
3. Select plan: "Free"
4. Click "Continue"

### Cambiar nameservers

1. Cloudflare mostrará 2 nameservers
2. Ir a Hostgator → Domain Management
3. Cambiar nameservers a los de Cloudflare
4. Esperar propagación (5 min - 48h)

### Configurar SSL

1. En Cloudflare → SSL/TLS
2. Mode: "Full (strict)"
3. "Always Use HTTPS": ON
4. "Automatic HTTPS Rewrites": ON

### Configurar cache

1. En Cloudflare → Caching
2. Browser Cache TTL: "1 month"
3. Caching Level: "Standard"

---

## 6. UptimeRobot (Monitoreo) - 5 minutos

### Crear cuenta

1. Ir a https://uptimerobot.com
2. Click "Register for Free"
3. Crear cuenta

### Agregar monitor

1. Click "Add New Monitor"
2. Monitor Type: "HTTP(s)"
3. Friendly Name: `Tienda Eaciot`
4. URL: `https://tienda.eaciot.com/health`
5. Monitoring Interval: `5 minutes`
6. Click "Create Monitor"

### Configurar alertas

1. Ir a My Settings → Alert Contacts
2. Agregar email
3. Asociar al monitor

---

## 7. Backblaze B2 (Storage) - 10 minutos

### Crear cuenta

1. Ir a https://www.backblaze.com/b2
2. Click "Sign Up"
3. Crear cuenta (requiere tarjeta, pero no cobra)

### Crear bucket

1. Ir a "Buckets"
2. Click "Create a Bucket"
3. Bucket Name: `tienda-eaciot-files`
4. Files are: "Public"
5. Click "Create"

### Crear application key

1. Ir a "App Keys"
2. Click "Add a New Application Key"
3. Name: `tienda-eaciot`
4. Click "Create"
5. **COPIAR**:
   - keyID
   - applicationKey

### Configurar .env

```
B2_KEY_ID=xxxx
B2_APPLICATION_KEY=xxxx
B2_BUCKET_NAME=tienda-eaciot-files
B2_ENDPOINT=https://s3.us-east-005.backblazeb2.com
```

---

## VERIFICACIÓN FINAL

### Checklist

- [ ] Supabase: Connection string funciona
- [ ] SendGrid: API key creada, remitente verificado
- [ ] Sentry: DSN copiado
- [ ] Upstash: Redis URL copiada
- [ ] Cloudflare: Dominio agregado, SSL activo
- [ ] UptimeRobot: Monitor creado
- [ ] Backblaze: Bucket creado, keys copiadas

### Test rápido

```bash
# Verificar conexión DB
python -c "from app.database import engine; print('DB OK')"

# Verificar email
python -c "from app.services.email_service import email_service; print('Email OK')"

# Verificar Redis (opcional)
python -c "import redis; r = redis.from_url('xxx'); print('Redis OK')"
```

---

## TROUBLESHOOTING

### Supabase: "Connection refused"
- Verificar que la contraseña sea correcta
- Verificar que el proyecto esté activo

### SendGrid: "Authentication failed"
- Verificar que SMTP_USER sea "apikey"
- Verificar que la API key sea correcta

### Sentry: "DSN not configured"
- Verificar que SENTRY_DSN esté en .env
- Verificar formato: `https://xxx@xxx.ingest.sentry.io/xxx`

### Cloudflare: "SSL not working"
- Esperar propagación DNS (hasta 48h)
- Verificar SSL mode sea "Full (strict)"

---

## COSTOS

| Servicio | Plan Gratis | Límite |
|----------|-------------|--------|
| Supabase | Free | 500MB DB |
| SendGrid | Free | 100 emails/día |
| Sentry | Free | 5k errors/mes |
| Upstash | Free | 10k cmds/día |
| Cloudflare | Free | Ilimitado |
| UptimeRobot | Free | 50 monitors |
| Backblaze | Free | 10GB storage |
| **TOTAL** | **$0/mes** | |
