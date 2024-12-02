#!/bin/bash
set -e

echo "Starting application..."
echo "Environment: $DJANGO_ENV"
echo "Port: $PORT"

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis to be ready..."
    echo "Checking Redis at localhost:6379..."

    local attempts=0
    local max_attempts=30

    while [ $attempts -lt $max_attempts ]; do
        if nc -z localhost 6379; then
            echo "Redis is ready!"
            return 0
        fi

        attempts=$((attempts + 1))
        echo "Redis not ready (attempt $attempts/$max_attempts) - sleeping 1s"
        sleep 1
    done

    echo "Redis connection timeout after $max_attempts attempts"
    return 1
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
    echo "Workers: ${GUNICORN_WORKERS:-2}"

    # Using sync worker with preload for better memory efficiency
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers ${GUNICORN_WORKERS:-2} \
        --worker-class sync \
        --preload \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --log-level ${LOG_LEVEL:-info} \
        --access-logfile - \
        --error-logfile - \
        --timeout ${GUNICORN_TIMEOUT:-120} \
        --graceful-timeout 30 \
        --keep-alive 65 \
        --max-child-requests 1000
else
    echo "Starting Django development server..."
    exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi
