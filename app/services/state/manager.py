"""Clean state management implementation"""
import json
import logging
from typing import Any, Dict

from redis.exceptions import RedisError
from .data import StateData
from .config import RedisConfig

logger = logging.getLogger(__name__)


class StateManager:
    """Simple Redis-backed state management"""

    def __init__(self, redis_client=None):
        """Initialize with Redis client or create new one"""
        self.redis = redis_client or RedisConfig().get_client()
        self.ttl = 3600  # 1 hour TTL
        self.key_prefix = "user_state:"

    def _get_key(self, user_id: str) -> str:
        """Generate Redis key for user state"""
        return f"{self.key_prefix}{user_id}"

    def get(self, user_id: str) -> Dict[str, Any]:
        """Get user state, creating empty if none exists"""
        try:
            key = self._get_key(user_id)
            data = self.redis.get(key)

            if not data:
                return StateData.create_default()

            # Parse stored state if needed
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    logger.error(f"Corrupted state data for user {user_id}")
                    return StateData.create_default()

            return data

        except RedisError as e:
            logger.error(f"Redis error getting state: {str(e)}")
            return StateData.create_default()

    def set(self, user_id: str, state: Dict[str, Any]) -> None:
        """Set complete user state"""
        try:
            if not isinstance(state, dict):
                raise ValueError("State must be a dictionary")

            # Store state
            key = self._get_key(user_id)
            self.redis.set(key, json.dumps(state), ex=self.ttl)

        except RedisError as e:
            logger.error(f"Redis error setting state: {str(e)}")
            raise

    def update(self, user_id: str, data: Dict[str, Any]) -> None:
        """Update existing state with new data"""
        try:
            # Get current state
            current = self.get(user_id)

            # Merge states preserving critical fields
            updated = StateData.merge(current, data)

            # Store updated state
            self.set(user_id, updated)

        except RedisError as e:
            logger.error(f"Redis error updating state: {str(e)}")
            raise

    def clear(self, user_id: str) -> None:
        """Clear user state"""
        try:
            key = self._get_key(user_id)
            self.redis.delete(key)
        except RedisError as e:
            logger.error(f"Redis error clearing state: {str(e)}")
            raise
