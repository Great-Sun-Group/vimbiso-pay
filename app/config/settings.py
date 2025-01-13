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
    "django.contrib.sessions",  # For Redis session storage
    "corsheaders",  # For API security
    "core.config.apps.CoreConfig",  # Core bot app
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",  # For Redis session support
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

# Database configuration - using in-memory SQLite since we only use Redis for state
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Pure in-memory database, no file access needed
    }
}

# Redis configuration
REDIS_URL = env("REDIS_URL", default="redis://redis-state:6379/0")

# Cache configuration using Redis - shared with application state management
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,  # seconds
            "SOCKET_TIMEOUT": 5,  # seconds
            "RETRY_ON_TIMEOUT": True,
            "MAX_CONNECTIONS": 10,
            "HEALTH_CHECK_INTERVAL": 30,  # seconds
            "CONNECTION_POOL_CLASS": "redis.ConnectionPool",
            # Removed PARSER_CLASS since it's causing issues with newer Redis versions
            "REDIS_CLIENT_KWARGS": {
                "decode_responses": True  # Match existing client configuration
            }
        },
        "KEY_PREFIX": "vimbiso",  # Namespace cache keys
        "TIMEOUT": None,  # Disable cache timeouts since we're using it for state
    }
}

# Use Redis as the session backend as well for consistency
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Security settings
CORS_ALLOW_HEADERS = ["apiKey"]  # For WhatsApp webhook
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        # Core application logging
        "core": {
            "handlers": ["console"],
            "level": env("APP_LOG_LEVEL", default="DEBUG"),
            "propagate": False,
        },
        # Django framework logging
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="WARNING"),
            "propagate": False,
        },
        # Third party libraries
        "urllib3": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Time zone
TIME_ZONE = "Africa/Harare"
USE_TZ = True

# Required Django setting
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
