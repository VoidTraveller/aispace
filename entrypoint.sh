#!/bin/bash
set -e

echo "Waiting for Postgres..."
until python -c "
import psycopg2, sys
from app.config import settings
try:
    psycopg2.connect(settings.database_url)
except Exception:
    sys.exit(1)
"; do
  sleep 1
done
echo "Postgres is ready."

echo "Running migrations..."
python -m alembic upgrade head

echo "Seeding rooms..."
python -m app.seed

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000