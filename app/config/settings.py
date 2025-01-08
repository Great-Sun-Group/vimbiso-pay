import os
from pathlib import Path
from decouple import config as env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Core settings
SECRET_KEY = env("DJANGO_SECRET")
DEBUG = env("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default="localhost 127.0.0.1").split(" ")

# Application definition
INSTALLED_APPS = [
    "django.contrib.auth",  # For basic auth
    "django.contrib.contenttypes",  # Required dependency
    "corsheaders",  # For API security
    "core.config.apps.CoreConfig",  # Core bot app
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Storage paths
DEPLOYED_TO_AWS = env('DEPLOYED_TO_AWS', default=False, cast=bool)
if DEPLOYED_TO_AWS:
    BASE_PATH = "/efs-vols/app-data/data"
else:
    BASE_PATH = BASE_DIR / 'data'
    os.makedirs(BASE_PATH, exist_ok=True)

# Redis state configuration
REDIS_STATE_URL = env("REDIS_STATE_URL", default="redis://redis-state:6379/0")

# Redis cache configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_STATE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Security settings
CORS_ALLOW_HEADERS = ["apiKey"]  # For WhatsApp webhook
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Basic logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "core": {
            "handlers": ["console"],
            "level": env("APP_LOG_LEVEL", default="DEBUG"),
        },
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
        },
    },
}

# Time zone
TIME_ZONE = "Africa/Harare"
USE_TZ = True

# Required Django setting
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
