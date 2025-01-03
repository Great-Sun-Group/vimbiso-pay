"""WhatsApp bot service implementation"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import ComponentException
from services.messaging.service import MessagingService

from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


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
            # Let ErrorHandler format error message
            error_context = ErrorContext(
                error_type="bot_service",
                message=str(e),
                details={
                    "payload": payload,
                    "message_type": message_type if 'message_type' in locals() else "unknown",
                    "message_text": message_text if 'message_text' in locals() else "unknown"
                }
            )
            error = ErrorHandler.handle_error(e, state_manager, error_context)

            return WhatsAppMessage.create_text(
                state_manager.get_channel_id(),
                error["message"]
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
