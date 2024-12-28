"""WhatsApp service state management delegating to core StateManager"""
import logging
from typing import Any, Dict

from core.config.state_manager import StateManager as CoreStateManager
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateManager:
    """WhatsApp state management delegating to core StateManager"""

    def __init__(self, state_manager: CoreStateManager):
        """Initialize with core state manager"""
        self._core = state_manager

    def get(self, key: str) -> Any:
        """Get state value using core state manager"""
        return self._core.get(key)

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state using core state manager

        Args:
            updates: State updates to apply

        Raises:
            StateException: If state update fails
        """
        # Let core state manager handle validation and updates
        self._core.update_state(updates)

        # Log transition
        audit.log_state_transition(
            "bot_service",
            {"status": "before_update"},
            {"status": "after_update"},  # Only log status
            "success"
        )
