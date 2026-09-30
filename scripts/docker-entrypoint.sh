#!/bin/sh
set -e

echo "=================================================="
echo "EdgeTwin AI — Backend Container Starting"
echo "=================================================="

# Apply database migrations if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "[MIGRATION] Applying database migrations via Alembic..."
    alembic -c api/alembic.ini upgrade head
    echo "[MIGRATION] Migrations applied successfully."
else
    echo "[MIGRATION] DATABASE_URL not set; skipping automated Alembic migration."
fi

# Execute main process
echo "[STARTUP] Starting FastAPI server on ${API_HOST:-0.0.0.0}:${API_PORT:-8000}..."
exec uvicorn api.app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
