"""Authentication handlers enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.types import Message
from core.utils.exceptions import StateException

from .handlers.auth.auth_flow import attempt_login, handle_registration
from .handlers.member.display import handle_menu, handle_refresh

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


def handle_action_menu(state_manager: Any) -> Message:
    """Display main menu or handle registration"""
    try:
        return handle_menu(state_manager)
    except StateException as e:
        return handle_error(state_manager, "Menu display", e)


def handle_action_hi(state_manager: Any) -> Message:
    """Handle initial greeting with login attempt"""
    try:
        # Always attempt login first
        success, error = attempt_login(state_manager)

        if success:
            # Login successful - show dashboard
            return handle_menu(state_manager)

        # Login failed - show welcome with registration button
        return handle_registration(state_manager)

    except StateException as e:
        return handle_error(state_manager, "Greeting", e)


def handle_action_refresh(state_manager: Any) -> Message:
    """Handle dashboard refresh"""
    try:
        return handle_refresh(state_manager)
    except StateException as e:
        return handle_error(state_manager, "Refresh", e)
