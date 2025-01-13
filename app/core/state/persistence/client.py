"""Redis client factory"""
from django_redis import get_redis_connection


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
    - HiredisParser for performance
    """
    return get_redis_connection("default")
