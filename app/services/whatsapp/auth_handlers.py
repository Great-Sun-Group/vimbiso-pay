"""Authentication and menu handlers enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Tuple, Dict

from .types import WhatsAppMessage
from .handlers.auth.auth_flow import (
    handle_registration,
    attempt_login
)
from .handlers.auth.menu_functions import (
    handle_menu,
    handle_hi,
    handle_refresh
)

logger = logging.getLogger(__name__)


def get_channel_id(state_manager: Any) -> str:
    """Get channel ID from state safely"""
    try:
        channel = state_manager.get("channel")
        if channel and channel.get("identifier"):
            return channel["identifier"]
    except ValueError:
        pass
    return "unknown"


def handle_error(state_manager: Any, operation: str, error: ValueError) -> WhatsAppMessage:
    """Handle errors consistently"""
    logger.error(f"{operation} failed: {str(error)}")
    return WhatsAppMessage.create_text(
        get_channel_id(state_manager),
        f"Error: {str(error)}"
    )


def handle_action_register(state_manager: Any, register: bool = False) -> WhatsAppMessage:
    """Handle registration flow"""
    try:
        return handle_registration(state_manager, register)
    except ValueError as e:
        return handle_error(state_manager, "Registration", e)


def handle_action_menu(state_manager: Any, message: str = None, login: bool = False) -> WhatsAppMessage:
    """Display main menu"""
    try:
        return handle_menu(state_manager, message, login)
    except ValueError as e:
        return handle_error(state_manager, "Menu display", e)


def handle_action_refresh(state_manager: Any) -> WhatsAppMessage:
    """Handle dashboard refresh"""
    try:
        return handle_refresh(state_manager)
    except ValueError as e:
        return handle_error(state_manager, "Refresh", e)


def handle_action_hi(state_manager: Any, credex_service: Any) -> Tuple[bool, Dict[str, Any]]:
    """Handle initial greeting with login attempt

    Args:
        state_manager: State manager instance
        credex_service: CredEx service instance for authentication

    Returns:
        Tuple[bool, Dict[str, Any]]: Success flag and response data
    """
    try:
        # Handle initial greeting
        handle_hi(state_manager)
        # Attempt login with service
        return attempt_login(state_manager, credex_service)
    except ValueError as e:
        logger.error(f"Login error: {str(e)}")
        return False, {"error": str(e)}
