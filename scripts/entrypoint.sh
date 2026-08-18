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

echo "=== entrypoint $(date -u) cwd=$(pwd) db=${DATABASE_URL:-unset} ===" >> "$AUDIT"

echo "== Tienda Eaciot: migraciones =="
alembic upgrade head 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py alembic || true

echo "== Tienda Eaciot: bootstrap (productos demo + admin, idempotente) =="
python scripts/bootstrap.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py bootstrap || true

echo "== Tienda Eaciot: revive de productos (one-shot) =="
python scripts/revive_products.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py revive || true

echo "== Tienda Eaciot: restaurar catálogo laptops/SSD (one-shot) =="
python scripts/restore_catalog.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py restore || true

echo "== Tienda Eaciot: enrich con el depto de marketing IA (best-effort) =="
python scripts/enrich_products.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py enrich || true

echo "== Tienda Eaciot: arrancando =="
# --proxy-headers + --forwarded-allow-ips: el proxy de la plataforma (Nixopus
# Caddy / Render / Traefik) termina TLS y reenvía en HTTP plano con
# X-Forwarded-Proto: https. Sin confiar en él, FORCE_HTTPS genera un bucle
# infinito de redirecciones https.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips '*'
