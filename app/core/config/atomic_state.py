"""Atomic state operations with validation tracking"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.utils.exceptions import SystemException
from core.utils.redis_atomic import RedisAtomic

logger = logging.getLogger(__name__)


class AtomicStateManager:
    """Atomic state operations with validation tracking"""

    def __init__(self, redis_client):
        """Initialize with Redis client"""
        self.storage = RedisAtomic(redis_client)
        self._validation_state = {
            "attempts": {},  # Track attempts per key
            "last_attempts": {},  # Track last attempt timestamps
            "errors": {}  # Track errors per key
        }

    def _track_attempt(self, key: str, operation: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Track operation attempt with validation state"""
        # Initialize tracking for key if needed
        if key not in self._validation_state["attempts"]:
            self._validation_state["attempts"][key] = {}
            self._validation_state["last_attempts"][key] = {}
            self._validation_state["errors"][key] = {}

        # Update attempt count
        self._validation_state["attempts"][key][operation] = \
            self._validation_state["attempts"][key].get(operation, 0) + 1

        # Update last attempt
        self._validation_state["last_attempts"][key][operation] = datetime.utcnow().isoformat()

        # Update error if present
        if error:
            self._validation_state["errors"][key][operation] = error
        else:
            self._validation_state["errors"][key][operation] = None

        # Return current validation state
        return {
            "in_progress": False,
            "attempts": self._validation_state["attempts"][key][operation],
            "last_attempt": self._validation_state["last_attempts"][key][operation],
            "error": self._validation_state["errors"][key][operation]
        }

    def atomic_get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get state with validation tracking"""
        success, data, error = self.storage.execute_atomic(key, 'get')
        validation = self._track_attempt(key, "get", error)

        if not success:
            raise SystemException(
                message=f"Failed to get state: {error}",
                code="STATE_GET_ERROR",
                service="atomic_state",
                action="get"
            )

        if data:
            data["_validation"] = validation

        return data

    def atomic_set(self, key: str, value: Dict[str, Any], ttl: int = 300) -> None:
        """Set state with validation tracking"""
        # Add validation state
        value["_validation"] = self._track_attempt(key, "set")

        success, _, error = self.storage.execute_atomic(
            key=key,
            operation='set',
            value=value,
            ttl=ttl
        )

        if not success:
            self._track_attempt(key, "set", error)
            raise SystemException(
                message=f"Failed to set state: {error}",
                code="STATE_SET_ERROR",
                service="atomic_state",
                action="set"
            )

    def atomic_update(self, key: str, value: Dict[str, Any], ttl: int = 300) -> None:
        """Update state with validation tracking"""
        # Add validation state
        value["_validation"] = self._track_attempt(key, "update")

        success, _, error = self.storage.execute_atomic(
            key=key,
            operation='set',
            value=value,
            ttl=ttl
        )

        if not success:
            self._track_attempt(key, "update", error)
            raise SystemException(
                message=f"Failed to update state: {error}",
                code="STATE_UPDATE_ERROR",
                service="atomic_state",
                action="update"
            )

    def atomic_delete(self, key: str) -> None:
        """Delete state with validation tracking"""
        success, _, error = self.storage.execute_atomic(key, 'delete')

        if not success:
            self._track_attempt(key, "delete", error)
            raise SystemException(
                message=f"Failed to delete state: {error}",
                code="STATE_DELETE_ERROR",
                service="atomic_state",
                action="delete"
            )
