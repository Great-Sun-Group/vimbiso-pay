import logging
from typing import Any, Dict, Optional
from datetime import datetime

from core.utils.exceptions import SystemException

logger = logging.getLogger(__name__)


class AtomicStateManager:
    """Atomic state manager using Django cache with validation tracking"""

    def __init__(self, cache_backend):
        self.cache = cache_backend
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
        """Get state with validation tracking

        Args:
            key: Cache key

        Returns:
            State data if found, None if not found

        Raises:
            SystemException: If cache operation fails
        """
        try:
            logger.debug(f"Attempting to get state from Redis for key: {key}")
            state_data = self.cache.get(key)
            logger.debug(f"Retrieved state data from Redis: {state_data}")
            validation = self._track_attempt(key, "get")

            if state_data:
                state_data["_validation"] = validation
                logger.debug(f"Added validation to state data: {state_data}")

            return state_data

        except Exception as e:
            error = str(e)
            validation = self._track_attempt(key, "get", error)
            raise SystemException(
                message=f"Failed to get state: {error}",
                code="STATE_GET_ERROR",
                service="atomic_state",
                action="get"
            )

    def atomic_set(self, key: str, value: Dict[str, Any], ttl: int = 300) -> None:
        """Set state with validation tracking

        Args:
            key: Cache key
            value: State data to set
            ttl: Time to live in seconds

        Raises:
            SystemException: If cache operation fails
        """
        try:
            # Add validation state
            value["_validation"] = self._track_attempt(key, "set")

            self.cache.set(key, value, timeout=ttl)

        except Exception as e:
            error = str(e)
            self._track_attempt(key, "set", error)
            raise SystemException(
                message=f"Failed to set state: {error}",
                code="STATE_SET_ERROR",
                service="atomic_state",
                action="set"
            )

    def atomic_update(self, key: str, value: Dict[str, Any], ttl: int = 300) -> None:
        """Update state with validation tracking

        Args:
            key: Cache key
            value: State data to update
            ttl: Time to live in seconds

        Raises:
            SystemException: If cache operation fails
        """
        try:
            # Add validation state
            value["_validation"] = self._track_attempt(key, "update")
            logger.debug(f"Attempting to update Redis state for key {key} with value: {value}")

            self.cache.set(key, value, timeout=ttl)
            logger.debug(f"Successfully updated Redis state for key: {key}")

        except Exception as e:
            error = str(e)
            self._track_attempt(key, "update", error)
            raise SystemException(
                message=f"Failed to update state: {error}",
                code="STATE_UPDATE_ERROR",
                service="atomic_state",
                action="update"
            )
