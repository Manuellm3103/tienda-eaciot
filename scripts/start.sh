#!/usr/bin/env bash
set -e

echo "Starting Tienda Eaciot..."
# --proxy-headers --forwarded-allow-ips '*' :
# Render terminates TLS at its proxy and forwards to this container over plain
# HTTP with an X-Forwarded-Proto: https header. Without trusting it, uvicorn
# reports scheme=http and HTTPSRedirectMiddleware (FORCE_HTTPS=true) creates an
# infinite https redirect loop that makes the store look down.
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'
