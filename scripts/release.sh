#!/usr/bin/env bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Release phase complete."
