"""WhatsApp bot service implementation"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException
from services.messaging.service import MessagingService

from .service import WhatsAppMessagingService
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


def process_bot_message(payload: Dict[str, Any], state_manager: Any) -> WhatsAppMessage:
    """Process bot message through flow framework

    Args:
        payload: Message payload
        state_manager: State manager instance

    Returns:
        WhatsAppMessage: Formatted response for WhatsApp
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

        return WhatsAppMessage.create_text(
            state_manager.get_channel_id(),
            error_response["error"]["message"]
        )


def get_bot_service() -> 'BotService':
    """Get bot service instance through proper initialization"""
    # Create WhatsApp messaging service
    whatsapp_service = WhatsAppMessagingService(None)  # API client handled by service

    # Create messaging service with WhatsApp implementation
    messaging_service = MessagingService(whatsapp_service)

    # Create and return bot service
    return BotService(messaging_service)


class BotService:
    """WhatsApp bot service using messaging service interface"""

    def __init__(self, messaging_service: MessagingService):
        """Initialize with messaging service"""
        self.messaging = messaging_service

    def process_message(self, payload: Dict[str, Any], state_manager: Any) -> WhatsAppMessage:
        """Process bot message using messaging service

        Args:
            payload: Message payload
            state_manager: State manager instance

        Returns:
            WhatsAppMessage: Formatted response for WhatsApp
        """
        try:
            # Extract message data
            message_data = self._extract_message_data(payload)

            # Extract message content
            message_type = message_data.get("type", "")
            message_text = message_data.get("text", {}).get("body", "") if message_type == "text" else ""

            # Process through messaging service
            message = self.messaging.handle_message(
                state_manager=state_manager,
                message_type=message_type,
                message_text=message_text
            )

            # Convert to WhatsApp format
            return WhatsAppMessage.from_core_message(message)

        except Exception as e:
            # Handle system errors
            error_response = ErrorHandler.handle_system_error(
                code="BOT_ERROR",
                service="bot_service",
                action="process_message",
                message=str(e),
                error=e
            )

            return WhatsAppMessage.create_text(
                state_manager.get_channel_id(),
                error_response["error"]["message"]
            )

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
