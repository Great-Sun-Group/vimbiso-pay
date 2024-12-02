#!/bin/bash
set -e

echo "Starting application..."
echo "Environment: $DJANGO_ENV"
echo "Port: $PORT"

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
max_attempts=30
attempt=1

while ! redis-cli -h 127.0.0.1 ping > /dev/null 2>&1; do
    if [ $attempt -eq $max_attempts ]; then
        echo "Redis is still unavailable after $max_attempts attempts - giving up"
        exit 1
    fi
    echo "Redis is unavailable - sleeping (attempt $attempt/$max_attempts)"
    attempt=$((attempt + 1))
    sleep 2
done

echo "Redis is ready!"

# Create required directories if they don't exist
mkdir -p /app/data/{db,static,media,logs}
chmod -R 755 /app/data

# In production, run migrations and collect static files
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
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
