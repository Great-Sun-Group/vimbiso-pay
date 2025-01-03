from typing import Any, Dict, Optional, Tuple
from datetime import datetime


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

    def atomic_get(self, key: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Get state with validation tracking"""
        try:
            state_data = self.cache.get(key)
            validation = self._track_attempt(key, "get")

            if state_data:
                state_data["_validation"] = validation

            return state_data, None

        except Exception as e:
            error = str(e)
            validation = self._track_attempt(key, "get", error)
            return None, error

    def atomic_set(self, key: str, value: Dict[str, Any], ttl: int = 300) -> Optional[str]:
        """Set state with validation tracking"""
        try:
            # Add validation state
            value["_validation"] = self._track_attempt(key, "set")

            self.cache.set(key, value, timeout=ttl)
            return None

        except Exception as e:
            error = str(e)
            self._track_attempt(key, "set", error)
            return error

    def atomic_update(self, key: str, value: Dict[str, Any], ttl: int = 300) -> Tuple[bool, Optional[str]]:
        """Update state with validation tracking"""
        try:
            # Add validation state
            value["_validation"] = self._track_attempt(key, "update")

            self.cache.set(key, value, timeout=ttl)
            return True, None

        except Exception as e:
            error = str(e)
            self._track_attempt(key, "update", error)
            return False, error
