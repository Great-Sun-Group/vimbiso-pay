#!/bin/bash
set -e

echo "Starting application..."
echo "Environment: $DJANGO_ENV"
echo "Port: $PORT"

# In ECS, we use container dependencies instead of waiting for Redis
# The container won't start until Redis is healthy
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
