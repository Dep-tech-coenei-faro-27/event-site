#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations..."
    /app/.venv/bin/alembik upgrade head
fi

exec "$@"
