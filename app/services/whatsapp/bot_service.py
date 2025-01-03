"""WhatsApp bot service implementation"""
import logging
from typing import Any, Dict

from core.utils.exceptions import ComponentException, FlowException
from services.messaging.service import MessagingService

from .service import WhatsAppMessagingService
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


def process_bot_message(payload: Dict[str, Any], state_manager: Any) -> WhatsAppMessage:
    """Process bot message using messaging service

    Args:
        payload: Message payload
        state_manager: State manager instance

    Returns:
        WhatsAppMessage: Formatted response for WhatsApp
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

        # Initialize services
        whatsapp = WhatsAppMessagingService(api_client=None)  # API client injected elsewhere
        messaging = MessagingService(whatsapp)

        # Process through messaging service
        message = messaging.handle_message(
            state_manager=state_manager,
            message_type=message_type,
            message_text=message_text
        )

        # Convert core Message to WhatsAppMessage
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

    except (ComponentException, FlowException) as e:
        # Handle known errors
        logger.error(f"Bot service error: {str(e)}")
        return WhatsAppMessage.create_text(
            state_manager.get_channel_id(),
            f"❌ {str(e)}"
        )

    except Exception as e:
        # Handle unexpected errors
        logger.error("Bot service error", extra={
            "error": str(e),
            "message_type": message_type if 'message_type' in locals() else "unknown",
            "message_text": message_text if 'message_text' in locals() else "unknown"
        })
        return WhatsAppMessage.create_text(
            state_manager.get_channel_id(),
            "❌ An unexpected error occurred. Please try again."
        )
