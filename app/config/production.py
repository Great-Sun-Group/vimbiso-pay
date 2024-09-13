from .base import *

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Database
DATABASES = {
    'default': env.db(),
}

# Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "KEY_PREFIX": "imdb",
        "TIMEOUT": 60 * 15,  # in seconds: 60 * 15 (15 minutes)
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

RQ_QUEUES = {
    "default": {
        "HOST": env("REDIS_HOST"),
        "PORT": env.int("REDIS_PORT"),
        "DB": 0,
        "DEFAULT_TIMEOUT": 360
    }
}

CELERY_BROKER_REDIS_URL = env("REDIS_URL")
CACHE_TTL = 60 * 15

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True

# Logging
LOGGING['handlers']['file']['level'] = 'WARNING'
LOGGING['root'] = {
    'handlers': ['file', 'logstash'],
    'level': 'WARNING',
}