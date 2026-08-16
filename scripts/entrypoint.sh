#!/usr/bin/env bash
set -e

# Entrypoint del contenedor: migra, siembra (idempotente) y arranca.
# Sustituye al flujo releaseCommand de Render para cualquier host Docker
# (Nixopus, VPS, compose local). Seguro de ejecutar en cada arranque.

echo "== Tienda Eaciot: migraciones =="
alembic upgrade head

echo "== Tienda Eaciot: bootstrap (productos demo + admin, idempotente) =="
python scripts/bootstrap.py

echo "== Tienda Eaciot: arrancando =="
# --proxy-headers + --forwarded-allow-ips: el proxy de la plataforma (Nixopus
# Caddy / Render / Traefik) termina TLS y reenvía en HTTP plano con
# X-Forwarded-Proto: https. Sin confiar en él, FORCE_HTTPS genera un bucle
# infinito de redirecciones https.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips '*'
