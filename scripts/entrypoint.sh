#!/usr/bin/env bash
set -e

# Entrypoint del contenedor Docker (Render usa runtime=docker, así que ESTE
# es el script que realmente corre en producción — no el releaseCommand).
# Migra, siembra (idempotente), restaura catálogo (one-shot), enriquece con
# IA y arranca. Cada paso queda auditado en la BD (GET /release-audit) y en
# uploads/release_audit.txt.

AUDIT_DIR="${UPLOAD_DIR:-./uploads}"
mkdir -p "$AUDIT_DIR"
AUDIT="$AUDIT_DIR/release_audit.txt"

# ── Persistencia ──────────────────────────────────────────────────────────
# La BD debe vivir en el disco persistente (/var/data en Render), NO en el
# filesystem efímero del contenedor (./app.db se pierde en cada deploy).
# Si DATABASE_URL no está definido o apunta al ./app.db local, redirigir a
# /var/data/app.db y rescatar cualquier ./app.db previo que exista.
case "${DATABASE_URL:-}" in
  ""|*"/./app.db"|sqlite+aiosqlite:///app.db)
    if [ -d /var/data ] && [ -w /var/data ]; then
      if [ -f ./app.db ] && [ ! -f /var/data/app.db ]; then
        cp -f ./app.db /var/data/app.db
        echo "PERSIST: ./app.db -> /var/data/app.db (rescate)" >> "$AUDIT"
      fi
      export DATABASE_URL="sqlite+aiosqlite:////var/data/app.db"
      echo "PERSIST: DATABASE_URL -> $DATABASE_URL" >> "$AUDIT"
    fi
    ;;
esac

echo "=== entrypoint $(date -u) cwd=$(pwd) db=${DATABASE_URL:-unset} ===" >> "$AUDIT"

echo "== Tienda Eaciot: migraciones =="
alembic upgrade head 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py alembic || true

echo "== Tienda Eaciot: bootstrap (productos demo + admin, idempotente) =="
python scripts/bootstrap.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py bootstrap || true

echo "== Tienda Eaciot: revive de productos (one-shot) =="
python scripts/revive_products.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py revive || true

echo "== Tienda Eaciot: restaurar catálogo laptops/SSD (one-shot) =="
python scripts/restore_catalog.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py restore || true
echo "== Tienda Eaciot: importar catálogo HP OmniBook (borradores, idempotente) =="
python scripts/import_hp_omnibook.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py hp || true

echo "== Tienda Eaciot: enrich depto marketing IA (background, no bloquea el arranque) =="
# En background para que uvicorn arranque al instante y el health check de
# Render pase. ~77s por producto; 25 productos ≈ 30 min generándose mientras
# la tienda ya está en línea (idempotente: retoma donde se quedó).
( python scripts/enrich_products.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py enrich ) &

echo "== Tienda Eaciot: arrancando =="
# --proxy-headers + --forwarded-allow-ips: el proxy de la plataforma (Nixopus
# Caddy / Render / Traefik) termina TLS y reenvía en HTTP plano con
# X-Forwarded-Proto: https. Sin confiar en él, FORCE_HTTPS genera un bucle
# infinito de redirecciones https.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips '*'
