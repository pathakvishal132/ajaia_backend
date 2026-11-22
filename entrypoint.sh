#!/bin/bash
set -e

echo "Waiting for database..."
while ! python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        dbname=os.environ.get('DB_NAME', 'collab_docs'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres'),
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
    )
    conn.close()
except Exception:
    exit(1)
" 2>/dev/null; do
    sleep 1
done

echo "Running migrations..."
python manage.py migrate --noinput

echo "Seeding users..."
python manage.py seed_users

echo "Starting server..."
exec "$@"
