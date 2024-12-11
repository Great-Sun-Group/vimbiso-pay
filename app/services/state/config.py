import os
from typing import Optional

import redis


class RedisConfig:
    """Redis configuration and client management"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
    ):
        """Initialize Redis configuration"""
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", "6379"))
        self.db = db or int(os.getenv("REDIS_DB", "0"))
        self.password = password or os.getenv("REDIS_PASSWORD", None)

    def get_client(self) -> redis.Redis:
        """Get Redis client instance"""
        return redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,  # Automatically decode response bytes to strings
        )

    @classmethod
    def from_env(cls) -> "RedisConfig":
        """Create Redis configuration from environment variables"""
        return cls()
