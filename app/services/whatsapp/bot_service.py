"""WhatsApp bot service implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from . import auth_handlers as auth
from .handlers.message import message_handler

logger = logging.getLogger(__name__)


def process_bot_message(payload: Dict[str, Any], state_manager: Any) -> Message:
    """Process bot message enforcing SINGLE SOURCE OF TRUTH

    Args:
        payload: Message payload
        state_manager: State manager instance

    Returns:
        Message: Core message type with recipient and content
    """
    if not state_manager:
        raise ValueError("State manager is required")

    try:
        # Extract message data
        message_type = payload.get("type", "")
        message_text = payload.get("text", "")

        # Handle message based on type
        if message_type == "text" and message_text.lower() == "hi":
            # Handle initial greeting
            return auth.handle_hi(state_manager)

        # Handle other messages
        return message_handler.process_message(
            state_manager,
            message_type,
            message_text
        )

    except ValueError as e:
        # Handle errors consistently
        return auth.handle_error(state_manager, "Bot service", e)
