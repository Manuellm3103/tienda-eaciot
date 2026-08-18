# Migración de Tienda Eaciot a self-hosting (VPS)

> Alternativa a Render para eliminar los cold-starts del plan free.
> Investigación de GitHub actualizada al **2026-08-18**.

## 1. Investigación GitHub — los candidatos

| Herramienta | ⭐ GitHub | Último commit | Licencia | Tipo |
|---|---|---|---|---|
| [Coolify](https://github.com/coollabsio/coolify) | **60,728** | 2026-08-18 | Apache-2.0 | PaaS completo (UI) |
| [Dokploy](https://github.com/dokploy/dokploy) | **36,693** | 2026-08-18 | Apache-2.0 (core) + módulos source-available | PaaS ligero (UI) |
| [Dokku](https://github.com/dokku/dokku) | 32,106 | 2026-08-17 | MIT | Mini-Heroku (solo CLI) |
| [CapRover](https://github.com/caprover/caprover) | 15,133 | 2026-08-16 | Apache-2.0 | PaaS (Docker+nginx) |
| [Kamal](https://github.com/basecamp/kamal) | 14,517 | 2026-08-12 | MIT | Deploy por CLI (sin UI) |

## 2. Las dos mejores alternativas

### 🥇 Coolify — la más completa (recomendada)
- 60.7k ⭐, desarrollo diario, Apache-2.0, community activa.
- UI web: conecta GitHub, despliega apps/BDs, backups, multi-servidor.
- Traefik integrado → HTTPS con Let's Encrypt automático por dominio.
- **Ideal si quieres un "Render propio" con panel web.**

### 🥈 Dokploy — la más ligera y moderna
- 36.7k ⭐, UI más limpia, usa Docker Swarm para escalar.
- Menor huella de recursos que Coolify (mejor para un VPS pequeño).
- Backups automáticos a almacenamiento externo.
- **Ideal si quieres menos consumo de RAM/CPU.**

Ambas son 100 % gratuitas de self-hosting: solo pagas el VPS.

## 3. VPS barato (dónde hostear)

| Proveedor | Plan | Precio | Notas |
|---|---|---|---|
| **Hetzner** CX22 | 2 vCPU / 4 GB / 40 GB | ~€4/mes | Mejor precio/rendimiento (UE/USA) |
| **Contabo** VPS 1 | 4 vCPU / 6 GB | ~$6/mes | Mucho por tu dinero |
| **RackNerd** | 1 vCPU / 1 GB | ~$11/**año** | Promociones para probar |

Mínimo recomendado: **2 vCPU / 4 GB RAM / 20 GB SSD** (alcanza para el panel + la tienda + SQLite). Ubuntu 22.04 o 24.04.

## 4. Guía paso a paso

### Opción A — Coolify

1. **Crea el VPS** (Hetzner/Contabo) con Ubuntu, abre los puertos 22, 80 y 443.
2. **Instala Coolify** (1 comando como root):
   ```bash
   curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
   ```
3. Abre `http://IP_DEL_VPS:8000` y crea el usuario admin.
4. **Conecta el repo**: Settings → GitHub App → autoriza `Manuellm3103/tienda-eaciot`.
5. **Nueva aplicación** → *Application* → repositorio → *Build Pack: Docker Compose* (usa el `docker-compose.yml` ya subido). Si prefieres lo mínimo, usa *Dockerfile* + puerto `8000`.
6. **Dominio**: escribe `tienda.eaciot.com` → Coolify configura Traefik + TLS solo.
7. **Variables de entorno** (pega de `.env.example`, rellena los secretos):
   - `APP_SECRET_KEY` (uno fuerte; genera con `python scripts/generate_secret.py`)
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD` (el bootstrap crea el admin)
   - `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`
   - `OPENCODE_HOST`, `OPENCODE_MODEL`, `OPENCODE_API_KEY` (o `OLLAMA_*`)
   - `FRONTEND_URL=https://tienda.eaciot.com`, `FORCE_HTTPS=true`
8. **Volumen persistente** (solo si usaste *Dockerfile*): en *Storages* crea un volumen `app-data` montado en `/var/data`. Con *Docker Compose* el volumen ya está declarado.
9. **Deploy** → verifica `https://tienda.eaciot.com/health` (debe dar 200).
10. **Datos**: el catálogo y el contenido SEO **se auto-restauran** al arrancar (scripts del entrypoint). Si quieres conservar pedidos/clientes/reseñas, baja `app.db` de Render y súbelo al volumen `app-data` (`scp app.db root@IP:/var/lib/docker/volumes/.../_data/app.db`).
11. **Corta DNS**: apunta el registro A de `tienda.eaciot.com` a la IP del VPS (TTL bajo). Deja Render de respaldo hasta confirmar.

### Opción B — Dokploy (más ligera)

1. Crea el VPS igual que arriba.
2. **Instala Dokploy**:
   ```bash
   curl -fsSL https://dokploy.com/install.sh | sh
   ```
3. Abre `http://IP_DEL_VPS:3000` y crea el admin.
4. Conecta el repo GitHub y crea un *Service* con *Docker Compose* (o *Dockerfile* + puerto 8000).
5. Configura dominio `tienda.eaciot.com` (Traefik + TLS automáticos).
6. Pega las mismas variables de entorno del paso 7 de Coolify.
7. Deploy + verifica `/health` + corta DNS igual.

## 5. Backups (desde el día 1)

Tu SQLite vive en el volumen `app-data`. Con Coolify/Dokploy activa el backup automático del volumen a un bucket (S3/R2/Backblaze ~$0.005/GB) o a otro VPS.

Backup manual (cron diario en el VPS):
```bash
0 3 * * * docker exec tienda-eaciot sqlite3 /var/data/app.db ".backup '/var/data/app-backup.db'" && scp /var/data/app-backup.db user@backup:/backups/
```

## 6. Checklist final de corte

- [ ] `/health` responde 200 en el VPS
- [ ] Login admin funciona (bootstrap creó el admin)
- [ ] Checkout de prueba con Stripe test
- [ ] Webhooks de Stripe apuntan a `https://tienda.eaciot.com/api/payments/webhook`
- [ ] DNS `tienda.eaciot.com` → IP del VPS
- [ ] Render sigue de respaldo (no borres hasta estabilizar)
