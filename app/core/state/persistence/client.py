"""Redis client factory"""
import redis
from decouple import config


def get_redis_client() -> redis.Redis:
    """Get Redis client using environment configuration

    Returns:
        Redis client instance

    The client is configured with:
    - decode_responses=True to automatically decode Redis responses to strings
    - health_check_interval=30 to detect connection issues
    - retry_on_timeout=True to handle temporary connection issues
    """
    url = config("REDIS_URL", default="redis://redis-state:6379/0")
    return redis.from_url(
        url,
        decode_responses=True,
        health_check_interval=30,
        retry_on_timeout=True
    )
