"""Redis client factory"""
import warnings

from django.core.cache import CacheKeyWarning, cache
from django_redis.client.default import DefaultClient


def get_redis_client():
    """Get Redis client using Django's cache framework

    Returns:
        Redis client instance

    Uses Django's cache framework to get a Redis connection from the connection pool.
    The connection is configured in Django settings with:
    - decode_responses=True
    - health_check_interval=30
    - retry_on_timeout=True
    - Connection pooling
    - Automatic parser selection

    Note:
        Suppresses CacheKeyWarning since we're using Redis for state management,
        not traditional caching, so key format warnings aren't relevant.
    """
    # Suppress cache key warnings since we're using Redis for state management
    warnings.filterwarnings("ignore", category=CacheKeyWarning)

    # Get the raw Redis client from django-redis
    if not isinstance(cache.client, DefaultClient):
        raise RuntimeError("Cache backend is not django-redis DefaultClient")

    return cache.client.get_client(write=True)  # write=True ensures we get a client that can pipeline
