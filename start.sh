#!/bin/bash
# Production start: migrate, seed demo accounts (idempotent), then serve.
set -e
python manage.py migrate --noinput
python manage.py seed_users
exec gunicorn config.wsgi:application --bind 0.0.0.0:"${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60
