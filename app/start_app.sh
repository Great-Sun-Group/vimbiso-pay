#!/bin/bash
set -e

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis to be ready..."
    until redis-cli -h redis ping &>/dev/null; do
        echo "Redis is unavailable - sleeping"
        sleep 1
    done
    echo "Redis is ready!"
}

# Wait for Redis to be ready
wait_for_redis

# Apply database migrations if not running in development
# (development environment handles migrations in docker-compose)
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
fi

# Determine environment and set appropriate server command
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Starting Gunicorn server in production mode..."
    # Using fewer workers but more threads for better SQLite concurrency
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers ${GUNICORN_WORKERS:-2} \
        --worker-class gthread \
        --threads ${GUNICORN_THREADS:-4} \
        --worker-tmp-dir /dev/shm \
        --log-level ${LOG_LEVEL:-info} \
        --access-logfile - \
        --error-logfile - \
        --timeout ${GUNICORN_TIMEOUT:-120} \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --graceful-timeout 30 \
        --keep-alive 65
else
    echo "Starting Django development server..."
    exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi
