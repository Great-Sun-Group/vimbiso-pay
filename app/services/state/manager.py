"""Clean state management implementation"""
import json
import logging
from typing import Dict, Any

from redis.exceptions import RedisError
from .data import StateData

logger = logging.getLogger(__name__)


class StateManager:
    """Simple Redis-backed state management"""

    def __init__(self, redis_client):
        """Initialize with Redis client"""
        self.redis = redis_client
        self.ttl = 3600  # 1 hour TTL
        self.key_prefix = "user_state:"

        # Verify Redis connection
        try:
            if not self.redis.ping():
                raise ConnectionError("Redis ping failed")
        except RedisError as e:
            logger.error("Failed to connect to Redis")
            raise ConnectionError("Could not connect to Redis") from e

    def _get_key(self, user_id: str) -> str:
        """Generate Redis key for user state"""
        return f"{self.key_prefix}{user_id}"

    def get(self, user_id: str) -> Dict[str, Any]:
        """Get user state, creating default if none exists"""
        try:
            key = self._get_key(user_id)
            data = self.redis.get(key)

            if not data:
                return StateData.create_default()

            # Parse stored state
            try:
                if isinstance(data, str):
                    state = json.loads(data)
                else:
                    state = json.loads(data.decode('utf-8'))

                # Validate and ensure structure
                if not StateData.validate(state):
                    logger.error(f"Invalid state structure for user {user_id}")
                    return StateData.create_default()

                return state

            except json.JSONDecodeError:
                logger.error(f"Corrupted state data for user {user_id}")
                return StateData.create_default()

        except RedisError as e:
            logger.error(f"Redis error getting state: {str(e)}")
            raise

    def set(self, user_id: str, state: Dict[str, Any]) -> None:
        """Set complete user state"""
        try:
            # Validate state
            if not isinstance(state, dict):
                raise ValueError("State must be a dictionary")

            # Ensure valid structure
            if not StateData.validate(state):
                raise ValueError("Invalid state structure")

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

            # Update with new data
            current.update(data)

            # Store updated state
            self.set(user_id, current)

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
