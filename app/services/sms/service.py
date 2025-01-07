"""SMS messaging service stub for future implementation"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.base import BaseMessagingService
from core.messaging.types import Message, MessageRecipient
logger = logging.getLogger(__name__)


class SMSMessagingService(BaseMessagingService):
    """
    SMS implementation of messaging service.

    Note: This is a stub for future SMS channel implementation.
    Core functionality will be implemented after WhatsApp channel is stable.
    """

    def __init__(self):
        """Initialize SMS messaging service"""
        super().__init__()
        self.state_manager = None  # Will be set by MessagingService

    def _is_mock_mode(self) -> bool:
        """Check if service is in mock testing mode"""
        return hasattr(self, 'state_manager') and self.state_manager.get('mock_testing')

    def _send_message(self, message: Message) -> Message:
        """Send message through SMS API or mock

        Args:
            message: Core Message object to send

        Returns:
            Message: Sent message with metadata

        Raises:
            NotImplementedError: SMS channel not yet implemented
        """
        # Handle mock mode
        if self._is_mock_mode():
            message.metadata = {
                "sms_message_id": "mock_message_id",
                "mock": True
            }
            return message

        # Production mode not implemented
        raise NotImplementedError("SMS channel not yet implemented")

    def send_template(
        self,
        recipient: MessageRecipient,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send template message through SMS (not implemented)"""
        raise NotImplementedError("SMS channel not yet implemented")

    def authenticate_user(self, channel_type: str, channel_id: str) -> Dict[str, Any]:
        """Authenticate user with phone number (not implemented)"""
        raise NotImplementedError("SMS channel not yet implemented")
