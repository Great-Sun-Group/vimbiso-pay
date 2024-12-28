"""Authentication handlers enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.types import Message
from core.utils.exceptions import StateException

from .handlers.auth.auth_flow import attempt_login, handle_registration
from .handlers.member.display import handle_dashboard_display

logger = logging.getLogger(__name__)


def handle_error(state_manager: Any, operation: str, error: Exception) -> Message:
    """Handle errors consistently"""
    logger.error(f"{operation} failed: {str(error)}")
    # Let StateManager validate through state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": "registration",
            "step": 0,
            "current_step": "welcome",
            "data": {
                "error": str(error)  # Include error in state for audit
            }
        }
    })
    return handle_registration(state_manager)


def handle_hi(state_manager: Any) -> Message:
    """Handle greeting with login attempt"""
    try:
        # Attempt login (updates state internally)
        success, error = attempt_login(state_manager)
        if not success:
            return handle_registration(state_manager)

        # Login successful - show dashboard
        return handle_dashboard_display(state_manager)

    except StateException as e:
        return handle_error(state_manager, "Greeting", e)
