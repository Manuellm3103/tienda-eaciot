#!/usr/bin/env bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Bootstrapping demo products + admin user (idempotent)..."
python scripts/bootstrap.py

echo "Reviving inactive products if AUTO_REVIVE_PRODUCTS is set (one-shot recovery)..."
python scripts/revive_products.py || echo "Revive skipped (never blocks the deploy)"

echo "Enriching products with the AI marketing department (best-effort)..."
python scripts/enrich_products.py || echo "Enrich skipped (never blocks the deploy)"

echo "Release phase complete."
