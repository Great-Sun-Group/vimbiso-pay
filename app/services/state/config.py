"""Redis configuration for state management"""
import redis
from decouple import config as env
from urllib.parse import urlparse


class RedisConfig:
    """Redis configuration with optimized settings for state management"""

    def __init__(self):
        # Parse Redis URL
        url = env("REDIS_URL", default="redis://localhost:6379/0")
        parsed = urlparse(url)

        # Basic settings
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 6379
        self.password = parsed.password
        self.db = 1  # Use DB 1 for state management

        # Connection settings
        self.connection_settings = {
            "socket_timeout": 30,
            "socket_connect_timeout": 30,
            "retry_on_timeout": True,
            "health_check_interval": 30,
            "max_connections": 20,
            "decode_responses": True,
            "charset": "utf-8",
            "encoding": "utf-8"
        }

    def get_client(self) -> redis.Redis:
        """Get Redis client instance optimized for state management"""
        client = redis.Redis(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db,
            **self.connection_settings
        )

        # Configure Redis settings
        try:
            # Memory and persistence settings
            config = {
                "maxmemory": "256mb",
                "maxmemory-policy": "allkeys-lru",
                "appendonly": "yes",
                "appendfsync": "everysec",
                "save": ""  # Disable RDB snapshots
            }

            for key, value in config.items():
                client.config_set(key, value)

        except redis.RedisError as e:
            # Log error but don't fail - Redis will use defaults
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not configure Redis settings: {str(e)}")

        return client
