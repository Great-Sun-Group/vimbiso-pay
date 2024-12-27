"""Authentication and menu handlers enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.types import Message, TextContent, MessageRecipient, ChannelIdentifier, ChannelType
from .handlers.auth.auth_flow import (
    handle_registration
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


def handle_error(state_manager: Any, operation: str, error: ValueError) -> Message:
    """Handle errors consistently"""
    logger.error(f"{operation} failed: {str(error)}")
    channel_id = get_channel_id(state_manager)
    return Message(
        recipient=MessageRecipient(
            member_id=state_manager.get("member_id") or "unknown",
            channel_id=ChannelIdentifier(
                channel=ChannelType.WHATSAPP,
                value=channel_id
            )
        ),
        content=TextContent(
            body=f"Error: {str(error)}"
        )
    )


def handle_action_register(state_manager: Any, register: bool = False) -> Message:
    """Handle registration flow"""
    try:
        return handle_registration(state_manager, register)
    except ValueError as e:
        return handle_error(state_manager, "Registration", e)


def handle_action_menu(state_manager: Any) -> Message:
    """Display main menu"""
    try:
        return handle_menu(state_manager)
    except ValueError as e:
        return handle_error(state_manager, "Menu display", e)


def handle_action_refresh(state_manager: Any) -> Message:
    """Handle dashboard refresh"""
    try:
        return handle_refresh(state_manager)
    except ValueError as e:
        return handle_error(state_manager, "Refresh", e)


def handle_action_hi(state_manager: Any) -> Message:
    """Handle initial greeting with login attempt

    Args:
        state_manager: State manager instance

    Returns:
        Message: Core message type with recipient and content
    """
    try:
        # Handle initial greeting and return response
        return handle_hi(state_manager)
    except ValueError as e:
        logger.error(f"Login error: {str(e)}")
        return handle_error(state_manager, "Greeting", e)
