kill $(lsof -t -i:8000)
gunicorn config.wsgi:application --bind 0.0.0.0:8000  --workers 3 --log-level=info --log-file=- --access-logfile=- --timeout 120