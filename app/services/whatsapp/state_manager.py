"""WhatsApp service state management delegating to core StateManager"""
import logging
from typing import Any, Dict, Tuple

from core.config.state_manager import StateManager as CoreStateManager
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException

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
            StateException: If state access fails
        """
        try:
            return self._core.get(key)
        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message=f"Failed to get state value for key: {key}",
                details={
                    "key": key,
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, self, error_context))

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update state using core state manager

        Args:
            updates: State updates to apply

        Returns:
            Tuple of (success, error_message)

        Raises:
            StateException: If state update fails
        """
        try:
            # Log state update attempt
            logger.debug(
                "Updating state",
                extra={
                    "update_keys": list(updates.keys())
                }
            )

            # Let core state manager handle validation and updates
            result = self._core.update_state(updates)

            # Log success
            logger.info(
                "State updated successfully",
                extra={
                    "update_keys": list(updates.keys())
                }
            )

            return result

        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to update state",
                details={
                    "update_keys": list(updates.keys()),
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, self, error_context))
