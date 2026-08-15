#!/usr/bin/env bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Bootstrapping demo products + admin user (idempotent)..."
python scripts/bootstrap.py

echo "Release phase complete."
