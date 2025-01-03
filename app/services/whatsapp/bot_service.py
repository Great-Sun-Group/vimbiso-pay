"""WhatsApp bot service implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.exceptions import ComponentException, FlowException

from . import auth_handlers as auth
from .handlers.message.input_handler import get_action
from .handlers.message.message_handler import process_message
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


def process_bot_message(payload: Dict[str, Any], state_manager: Any) -> WhatsAppMessage:
    """Process bot message enforcing SINGLE SOURCE OF TRUTH

    Args:
        payload: Message payload
        state_manager: State manager instance

    Returns:
        Message: Core message type with recipient and content
    """
    try:
        # Validate state manager
        if not state_manager:
            raise ComponentException(
                message="State manager is required",
                component="bot_service",
                field="state_manager",
                value="None"
            )

        # Validate payload
        if not payload:
            raise ComponentException(
                message="Message payload is required",
                component="bot_service",
                field="payload",
                value="None"
            )

        # Let StateManager validate state by accessing a required field
        channel = state_manager.get("channel")
        if not channel:
            raise ComponentException(
                message="Channel information not found",
                component="bot_service",
                field="channel",
                value="None"
            )

        # Extract message data from WhatsApp payload
        try:
            value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
            message_data = value.get("messages", [{}])[0]
        except Exception:
            raise ComponentException(
                message="Invalid message payload format",
                component="bot_service",
                field="payload",
                value=str(payload)
            )

        # Extract message metadata
        message_type = message_data.get("type", "")
        message_text = message_data.get("text", {}).get("body", "") if message_type == "text" else ""

        # Handle message based on type
        if message_type == "text":
            # Get action from input handler (pass state_manager for flow check)
            action = get_action(message_text, state_manager, message_type)

            # Get current step for flow check
            current_step = state_manager.get_current_step()

            # Process through message handlers (returns core Message)
            message = None
            if action == "hi":
                # Handle greeting action (attempts login and shows dashboard)
                message = auth.handle_hi(state_manager)
            elif current_step:
                # In a flow - process message through flow handler
                message = process_message(state_manager, message_type, message_text, message_data)
            elif action:
                # Not in flow - handle normal actions
                message = process_message(state_manager, message_type, message_text.lower())
            else:
                # Default to dashboard for unrecognized input
                from .handlers.member.display import handle_dashboard_display
                message = handle_dashboard_display(state_manager)
        else:
            # Default to dashboard for non-text messages
            from .handlers.member.display import handle_dashboard_display
            message = handle_dashboard_display(state_manager)

        # Transform core Message to WhatsAppMessage
        if message.metadata and "error" in message.metadata:
            # Add error formatting for error messages
            return WhatsAppMessage.create_text(
                message.recipient.channel_value,
                f"❌ {message.content.body}"
            )
        else:
            # Pass through normal messages
            return WhatsAppMessage.create_text(
                message.recipient.channel_value,
                message.content.body
            )

    except (ComponentException, FlowException):
        # Handle known errors through message handler
        message = process_message(state_manager, message_type, message_text, message_data)
        return WhatsAppMessage.create_text(
            message.recipient.channel_value,
            f"❌ {message.content.body}"
        )

    except Exception:
        # Handle unexpected errors
        logger.error("Bot service error", extra={
            "message_type": message_type if 'message_type' in locals() else "unknown",
            "action": action if 'action' in locals() else "unknown"
        })
        # Let message handler create proper error message
        message = process_message(state_manager, message_type, message_text, message_data)
        return WhatsAppMessage.create_text(
            message.recipient.channel_value,
            f"❌ {message.content.body}"
        )
