"""WhatsApp messaging service implementation"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.types import Message
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppMessagingService:
    """Service for WhatsApp message handling"""

    def __init__(self, api_client: Any):
        """Initialize with API client"""
        self.api_client = api_client

    async def _send_message(self, message: Message) -> Dict[str, Any]:
        """Send a message via WhatsApp Cloud API"""
        try:
            # Convert core message to WhatsApp format
            whatsapp_message = WhatsAppMessage.from_core_message(message)

            # Send via API client
            response = await self.api_client.send_message(whatsapp_message)

            return response
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise

    async def get_template(self, template_name: str) -> Dict[str, Any]:
        """Get template details from WhatsApp"""
        try:
            return await self.api_client.get_template(template_name)
        except Exception as e:
            logger.error(f"Error getting template {template_name}: {str(e)}")
            raise

    async def send_template(
        self,
        recipient: str,
        template_name: str,
        language: str,
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a template message"""
        try:
            message = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language
                    }
                }
            }

            if components:
                message["template"]["components"] = components

            return await self.api_client.send_message(message)
        except Exception as e:
            logger.error(f"Error sending template {template_name}: {str(e)}")
            raise
