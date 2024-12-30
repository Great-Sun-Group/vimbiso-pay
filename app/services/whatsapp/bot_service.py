"""WhatsApp bot service implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.exceptions import StateException

from . import auth_handlers as auth
from .handlers.message.input_handler import get_action
from .handlers.message.message_handler import process_message

logger = logging.getLogger(__name__)


def process_bot_message(payload: Dict[str, Any], state_manager: Any) -> Message:
    """Process bot message enforcing SINGLE SOURCE OF TRUTH

    Args:
        payload: Message payload
        state_manager: State manager instance

    Returns:
        Message: Core message type with recipient and content
    """
    try:
        # Let StateManager validate state by accessing a required field
        state_manager.get("channel")

        # Extract message data from WhatsApp payload
        value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
        message_data = value.get("messages", [{}])[0]

        # Extract message metadata
        message_type = message_data.get("type", "")
        message_text = message_data.get("text", {}).get("body", "") if message_type == "text" else ""

        # Handle message based on type
        if message_type == "text":
            # Get action from input handler (pass state_manager for flow check)
            action = get_action(message_text, state_manager, message_type)

            if action == "hi":
                # Handle greeting action (attempts login and shows dashboard)
                return auth.handle_hi(state_manager)
            elif action:
                # Process message through appropriate handler
                return process_message(state_manager, message_type, message_text.lower())
            else:
                # Default to dashboard for unrecognized input
                from .handlers.member.display import handle_dashboard_display
                return handle_dashboard_display(state_manager)
        else:
            # Default to dashboard for non-text messages
            from .handlers.member.display import handle_dashboard_display
            return handle_dashboard_display(state_manager)

    except StateException as e:
        # Handle state validation errors consistently
        return auth.handle_error(state_manager, "Bot service", e)
