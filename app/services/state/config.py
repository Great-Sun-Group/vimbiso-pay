"""Redis configuration for state management"""
import redis
from django.conf import settings
from urllib.parse import urlparse


class RedisConfig:
    """Redis configuration with optimized settings for state management"""

    def __init__(self):
        # Use dedicated Redis instance for state management
        self.url = settings.REDIS_STATE_URL
        parsed = urlparse(self.url)

        # Basic settings
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 6380
        self.password = parsed.password
        self.db = int(parsed.path[1:]) if parsed.path else 0

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
        return redis.Redis(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db,
            **self.connection_settings
        )
