import os
import socket
from datetime import timedelta
from pathlib import Path

import redis
from corsheaders.defaults import default_headers
from decouple import config as env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = env("ALLOWED_HOSTS", default="localhost 127.0.0.1 bae2-129-222-164-135.ngrok-free.app").split(" ")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # Custom apps
    "core.config.apps.CoreConfig",
]

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

# Database configuration with environment-aware paths
DEPLOYED_TO_AWS = env('DEPLOYED_TO_AWS', default=False, cast=bool)

if DEPLOYED_TO_AWS:
    # Use EFS paths for production/staging
    DB_PATH = "/efs-vols/app-data/data/db/db.sqlite3"
    STATIC_ROOT = "/efs-vols/app-data/data/static"
    MEDIA_ROOT = "/efs-vols/app-data/data/media"
else:
    # Use local paths for development
    DB_PATH = BASE_DIR / 'data' / 'db' / 'db.sqlite3'
    STATIC_ROOT = BASE_DIR / 'data' / 'static'
    MEDIA_ROOT = BASE_DIR / 'data' / 'media'
    # Create necessary directories
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(STATIC_ROOT, exist_ok=True)
    os.makedirs(MEDIA_ROOT, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DB_PATH,
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {
            "timeout": 60,  # Increased timeout
            "isolation_level": "IMMEDIATE",  # Changed from READ_COMMITTED to IMMEDIATE
        },
        "CONN_MAX_AGE": 60,
    }
}

# Redis configuration
REDIS_CACHE_URL = env("REDIS_URL", default="redis://redis-cache:6379/0")
REDIS_STATE_URL = env("REDIS_STATE_URL", default="redis://redis-state:6379/0")

# Enhanced Redis Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    "state": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_STATE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}
# {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": REDIS_CACHE_URL,
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#             "SOCKET_CONNECT_TIMEOUT": 30,
#             "SOCKET_TIMEOUT": 30,
#             "RETRY_ON_TIMEOUT": True,
#             "MAX_CONNECTIONS": 20,
#             "CONNECTION_POOL_KWARGS": {
#                 "max_connections": 20,
#                 "retry_on_timeout": True,
#                 "retry_on_error": [
#                     redis.ConnectionError,
#                     redis.TimeoutError,
#                     socket.timeout,
#                     socket.error,
#                 ],
#                 "health_check_interval": 30,
#             },
#             "IGNORE_EXCEPTIONS": True,
#             "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
#             "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
#         },
#         "KEY_PREFIX": "vimbiso",
#         "TIMEOUT": 300,  # 5 minutes default timeout for cache keys
#     }

# Use Redis for session storage with optimized settings
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = False

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Harare"
USE_I18N = True
USE_TZ = True

# Static files (CSS JavaScript Images)
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework_xml.parsers.XMLParser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework_xml.renderers.XMLRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.utils.jwt_validators.EnhancedJWTAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/day", "user": "1000/day"},
}

# JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
    "AUTH_TOKEN_VALIDATORS": [
        "core.utils.jwt_validators.validate_token_user",
    ],
}

CORS_ALLOW_HEADERS = list(default_headers) + ["apiKey"]

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Production security settings
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^health/?$"]
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True

# Logging Configuration
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "handlers": {
#         "console": {
#             "class": "logging.StreamHandler",
#         },
#     },
#     "loggers": {
#         "": {
#             "handlers": ["console"],
#             "level": "INFO",
#         },
#     },
# }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": env("HANDLER_LOG_LEVEL", default="DEBUG"),  # Allow DEBUG through
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.utils.autoreload": {
            "handlers": ["console"],
            "level": "INFO",  # Reduce autoreload noise
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",  # Only log slow queries
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "level": env("APP_LOG_LEVEL", default="DEBUG"),  # Set core to DEBUG by default
            "propagate": False,
        },
        "django_redis": {
            "handlers": ["console"],
            "level": "WARNING",  # Only log important Redis issues
            "propagate": False,
        },
        "redis": {
            "handlers": ["console"],
            "level": "WARNING",  # Only log important Redis issues
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("ROOT_LOG_LEVEL", default="DEBUG"),  # Allow DEBUG through
    },
}

# Development-specific settings
if DEBUG:
    # Enable more detailed logging for specific components during development
    LOGGING["loggers"].update({
        "core": {
            "handlers": ["console"],
            "level": "DEBUG",  # Keep core app debugging
            "propagate": False,
        },
    })
