#!/usr/bin/env bash
# Release de Render. Todo se registra en uploads/release_audit.txt, que queda
# servible en https://tienda.eaciot.com/uploads/release_audit.txt (Render free
# no incluye Shell, así que este archivo es la ventana de depuración del
# release). Nunca escribe secretos.
set -e
set -o pipefail

AUDIT_DIR="${UPLOAD_DIR:-./uploads}"
mkdir -p "$AUDIT_DIR"
AUDIT="$AUDIT_DIR/release_audit.txt"

echo "=== release $(date -u) ===" >> "$AUDIT"
echo "flags: RESTORE_CATALOG=${RESTORE_CATALOG:-unset} AUTO_REVIVE_PRODUCTS=${AUTO_REVIVE_PRODUCTS:-unset} AUTO_ENRICH=${AUTO_ENRICH:-unset}" >> "$AUDIT"
echo "db: ${DATABASE_URL:-unset}" >> "$AUDIT"
echo "cwd: $(pwd)" >> "$AUDIT"

echo "Running database migrations..."
alembic upgrade head 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py alembic

echo "Bootstrapping demo products + admin user (idempotent)..."
python scripts/bootstrap.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py bootstrap || echo "bootstrap FAILED" >> "$AUDIT"

echo "Reviving inactive products if AUTO_REVIVE_PRODUCTS is set (one-shot recovery)..."
python scripts/revive_products.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py revive || echo "revive FAILED" >> "$AUDIT"

echo "Restoring catalog (laptops/SSD) if RESTORE_CATALOG is set (one-shot)..."
python scripts/restore_catalog.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py restore || echo "restore FAILED" >> "$AUDIT"

echo "Enriching products with the AI marketing department (best-effort)..."
python scripts/enrich_products.py 2>&1 | tee -a "$AUDIT" | python scripts/release_audit.py enrich || echo "enrich FAILED" >> "$AUDIT"

echo "Release phase complete." | tee -a "$AUDIT"
