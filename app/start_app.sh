#!/bin/bash
set -e

echo "Starting application..."
echo "Environment: $DJANGO_ENV"
echo "Port: $PORT"
echo "DEPLOYED_TO_AWS: ${DEPLOYED_TO_AWS:-false}"

# Debug Redis configuration
echo "REDIS_URL from environment: ${REDIS_URL:-not set}"
REDIS_HOST=$(echo "${REDIS_URL:-redis://localhost:6379/0}" | sed -E 's|redis://([^:/]+).*|\1|')
echo "Extracted Redis host: $REDIS_HOST"

# Test Redis connectivity with increased attempts to match task definition grace period
echo "Waiting for Redis to be ready..."
max_attempts=60  # Increased to match 300s grace period (5s * 60 = 300s)
attempt=1
wait_time=5  # Fixed 5s interval for predictable timing

while true; do
    if [ $attempt -gt $max_attempts ]; then
        echo "Redis is still unavailable after $max_attempts attempts - giving up"
        echo "Last Redis connection attempt output:"
        redis-cli -h "$REDIS_HOST" info | grep -E "^(# Server|redis_version|connected_clients|used_memory|used_memory_human|used_memory_peak|used_memory_peak_human|role)" || true
        echo "Redis process status:"
        ps aux | grep redis-server || true
        echo "Network status:"
        netstat -an | grep 6379 || true
        exit 1
    fi

    echo "Attempting Redis connection (attempt $attempt/$max_attempts waiting ${wait_time}s)..."

    if redis-cli -h "$REDIS_HOST" ping > /dev/null 2>&1; then
        echo "Redis connection successful!"
        echo "Redis server info:"
        redis-cli -h "$REDIS_HOST" info | grep -E "^(# Server|redis_version|connected_clients|used_memory|used_memory_human|used_memory_peak|used_memory_peak_human|role)"
        echo "Redis persistence status:"
        redis-cli -h "$REDIS_HOST" config get appendonly
        echo "Redis memory settings:"
        redis-cli -h "$REDIS_HOST" config get maxmemory
        redis-cli -h "$REDIS_HOST" config get maxmemory-policy
        break
    else
        echo "Redis connection failed. Server response:"
        redis-cli -h "$REDIS_HOST" ping || true
        echo "Checking Redis port status:"
        netstat -an | grep 6379 || true
        echo "Retrying in ${wait_time}s..."
        sleep $wait_time
        attempt=$((attempt + 1))
    fi
done

echo "Redis is ready!"

# Create required directories based on DEPLOYED_TO_AWS setting
if [ "${DEPLOYED_TO_AWS:-false}" = "true" ]; then
    echo "Using EFS storage..."
    # Ensure EFS mount directories exist
    mkdir -p /efs-vols/app-data/data/{static,media,logs}
    chmod -R 755 /efs-vols/app-data/data
else
    echo "Using local storage..."
    # Create local directories
    mkdir -p /app/data/{static,media,logs}
    chmod -R 755 /app/data
fi

# In production collect static files
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

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
        --keep-alive 65
else
    echo "Starting Django development server..."
    # Start Django with stdout/stderr going to console
    exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi
