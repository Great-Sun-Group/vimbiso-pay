"""WhatsApp state management delegating to core StateManager"""
import logging
from typing import Any, Dict, Tuple

from core.state.manager import StateManager as CoreStateManager
from core.error.exceptions import SystemException

logger = logging.getLogger(__name__)


class StateManager:
    """WhatsApp state management delegating to core StateManager"""

    def __init__(self, state_manager: CoreStateManager):
        """Initialize with core state manager"""
        self._core = state_manager

    def get(self, key: str) -> Any:
        """Get state value using core state manager

        Args:
            key: State key to retrieve

        Returns:
            State value for key

        Raises:
            SystemException: If state access fails
        """
        try:
            return self._core.get(key)
        except Exception as e:
            raise SystemException(
                message=f"Failed to get state value for key: {key}",
                code="STATE_GET_ERROR",
                service="whatsapp_state",
                action="get_state",
                details={
                    "key": key,
                    "error": str(e)
                }
            )

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update state using core state manager

        Args:
            updates: State updates to apply

        Returns:
            Tuple of (success, error_message)

        Raises:
            SystemException: If state update fails
        """
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Updating state")
            return self._core.update_state(updates)
        except Exception as e:
            raise SystemException(
                message="Failed to update state",
                code="STATE_UPDATE_ERROR",
                service="whatsapp_state",
                action="update_state",
                details={
                    "update_keys": list(updates.keys()),
                    "error": str(e)
                }
            )
