#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations..."
    /app/.venv/bin/alembic upgrade head
fi

exec "$@"
