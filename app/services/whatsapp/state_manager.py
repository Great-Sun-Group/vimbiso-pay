"""WhatsApp service state management delegating to core StateManager"""
import logging
from typing import Any, Dict, Optional, Tuple

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

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update state using core state manager"""
        try:
            # For flow_data updates, merge with existing flow data
            if "flow_data" in updates:
                current_flow = self._core.get("flow_data") or {}
                if isinstance(current_flow, dict) and isinstance(updates["flow_data"], dict):
                    merged_flow = current_flow.copy()
                    merged_flow.update(updates["flow_data"])
                    updates = {"flow_data": merged_flow}

            # Let core state manager handle validation and updates
            success = self._core.update_state(updates)
            if not success:
                return False, "State update failed"

            # Log transition
            audit.log_state_transition(
                "bot_service",
                {"flow_data": self._core.get("flow_data")},  # Only log flow data changes
                updates,
                "success"
            )

            return True, None

        except Exception as e:
            logger.error(f"State update error: {str(e)}")
            return False, str(e)
