#!/bin/sh
set -e

# Seed database on first run (sentinel file prevents re-seeding on restart)
if [ ! -f /app/data/.seeded ]; then
  echo "First run — seeding database..."
  cd /app && python -m scripts.seed_data
  touch /app/data/.seeded
  echo "Seed complete."
fi

exec python -m uvicorn main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --app-dir /app/src
