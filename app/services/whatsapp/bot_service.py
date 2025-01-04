"""WhatsApp bot service implementation"""
import logging
from typing import Any, Dict

from core.messaging.types import Message, TextContent
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException
from services.messaging.service import MessagingService
from services.messaging.utils import get_recipient

from .service import WhatsAppMessagingService

logger = logging.getLogger(__name__)


def process_bot_message(payload: Dict[str, Any], state_manager: Any) -> Message:
    """Process bot message through flow framework

    Args:
        payload: Message payload
        state_manager: State manager instance

    Returns:
        Message: Core message object for response
    """
    try:
        # Get bot service instance through proper initialization
        bot_service = get_bot_service()

        # Process through bot service
        return bot_service.process_message(payload, state_manager)

    except Exception as e:
        # Handle system errors
        error_response = ErrorHandler.handle_system_error(
            code="BOT_ERROR",
            service="bot_service",
            action="process_message",
            message=str(e),
            error=e
        )

        recipient = get_recipient(state_manager)
        content = TextContent(body=error_response["error"]["message"])
        return Message(recipient=recipient, content=content)


def get_bot_service() -> 'BotService':
    """Get bot service instance through proper initialization"""
    # Create WhatsApp messaging service for message formatting
    whatsapp_service = WhatsAppMessagingService()  # No API client needed - sending handled by send_whatsapp_message utility

    # Create messaging service with WhatsApp implementation
    messaging_service = MessagingService(whatsapp_service)

    # Create and return bot service
    return BotService(messaging_service)


class BotService:
    """WhatsApp bot service using messaging service interface"""

    def __init__(self, messaging_service: MessagingService):
        """Initialize with messaging service"""
        self.messaging = messaging_service

    def process_message(self, payload: Dict[str, Any], state_manager: Any) -> Message:
        """Process bot message using messaging service

        Args:
            payload: Message payload
            state_manager: State manager instance

        Returns:
            Message: Core message object for response
        """
        try:
            # Extract message data
            message_data = self._extract_message_data(payload)

            # Extract message content
            message_type = message_data.get("type", "")
            message_text = message_data.get("text", {}).get("body", "") if message_type == "text" else ""

            # Create message recipient
            recipient = get_recipient(state_manager)

            # Process through messaging service
            if message_type == "text":
                # Use messaging service's handle_message for full flow handling
                return self.messaging.handle_message(
                    state_manager=state_manager,
                    message_type=message_type,
                    message_text=message_text
                )

            # Fallback for unsupported message types
            logger.error(f"Unsupported message type: {message_type}")
            return self.messaging.send_text(
                recipient=recipient,
                text="Sorry, I can only handle text messages right now."
            )

        except Exception as e:
            # Handle system errors
            error_response = ErrorHandler.handle_system_error(
                code="BOT_ERROR",
                service="bot_service",
                action="process_message",
                message=str(e),
                error=e
            )

            recipient = get_recipient(state_manager)
            content = TextContent(body=error_response["error"]["message"])
            return Message(recipient=recipient, content=content)

    def _extract_message_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message data from WhatsApp payload"""
        if not payload:
            raise ComponentException(
                message="Message payload is required",
                component="bot_service",
                field="payload",
                value="None"
            )

        try:
            value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
            return value.get("messages", [{}])[0]
        except Exception:
            raise ComponentException(
                message="Invalid message payload format",
                component="bot_service",
                field="payload",
                value=str(payload)
            )
