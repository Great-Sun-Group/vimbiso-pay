#!/bin/bash
set -e

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Create health check endpoint
if [ ! -f "config/urls.py" ]; then
    echo "Error: config/urls.py not found"
    exit 1
fi

# Add health check endpoint if it doesn't exist
if ! grep -q "health" "config/urls.py"; then
    echo "Adding health check endpoint..."
    cat >> config/urls.py << 'EOF'

from django.http import HttpResponse
def health_check(request):
    return HttpResponse("OK")

urlpatterns += [
    path('health/', health_check, name='health_check'),
]
EOF
fi

# Determine environment and set appropriate server command
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Starting Gunicorn server in production mode..."
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 3 \
        --worker-class gthread \
        --threads 3 \
        --worker-tmp-dir /dev/shm \
        --log-level info \
        --access-logfile - \
        --error-logfile - \
        --timeout 120
else
    echo "Starting Django development server..."
    exec python manage.py runserver 0.0.0.0:8000
fi
