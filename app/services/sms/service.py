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

    def __init__(self, api_client: Any):
        """Initialize with SMS API client (not implemented)"""
        self.api_client = api_client

    def _send_message(self, message: Message) -> Dict[str, Any]:
        """Send message through SMS API (not implemented)"""
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
