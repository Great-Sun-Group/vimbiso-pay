"""WhatsApp bot service implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.exceptions import ComponentException, FlowException, SystemException

from . import auth_handlers as auth
from .handlers.message.input_handler import get_action
from .handlers.message.message_handler import process_message
from .types import WhatsAppMessage

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

            # Always handle hi/greeting first to allow refresh at any time
            if action == "hi":
                # Handle greeting action (attempts login and shows dashboard)
                return auth.handle_hi(state_manager)

            # Then check if we're in a flow
            current_step = state_manager.get_current_step()
            if current_step:
                # In a flow - process message through flow handler
                return process_message(state_manager, message_type, message_text, message_data)
            else:
                # Not in flow - handle normal actions
                if action:
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

    except ComponentException as e:
        # Handle validation errors
        logger.error(
            "Bot service validation error",
            extra={"error": str(e)}
        )
        return WhatsAppMessage.create_text(
            channel.get("identifier", "unknown"),
            f"❌ {str(e)}"
        )

    except FlowException as e:
        # Handle flow errors
        logger.error(
            "Bot service flow error",
            extra={"error": str(e)}
        )
        return WhatsAppMessage.create_text(
            channel.get("identifier", "unknown"),
            f"❌ {str(e)}"
        )

    except Exception as e:
        # Handle unexpected errors
        error = SystemException(
            message=str(e),
            code="BOT_SERVICE_ERROR",
            service="bot_service",
            action="process_message",
            details={
                "message_type": message_type if 'message_type' in locals() else None,
                "action": action if 'action' in locals() else None
            }
        )
        logger.error(
            "Bot service error",
            extra={"error": str(error)}
        )
        return WhatsAppMessage.create_text(
            channel.get("identifier", "unknown") if 'channel' in locals() else "unknown",
            f"❌ {str(error)}"
        )
