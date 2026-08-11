#!/usr/bin/env bash
set -e

echo "Starting Tienda Eaciot..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
