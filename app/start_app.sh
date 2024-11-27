#!/bin/bash
set -e

# Apply database migrations if not running in development
# (development environment handles migrations in docker-compose)
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
fi

# Determine environment and set appropriate server command
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Starting Gunicorn server in production mode..."
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers ${GUNICORN_WORKERS:-3} \
        --worker-class gthread \
        --threads ${GUNICORN_THREADS:-3} \
        --worker-tmp-dir /dev/shm \
        --log-level ${LOG_LEVEL:-info} \
        --access-logfile - \
        --error-logfile - \
        --timeout ${GUNICORN_TIMEOUT:-120}
else
    echo "Starting Django development server..."
    exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi
