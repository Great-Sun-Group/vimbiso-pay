"""WhatsApp messaging service implementation"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.base import BaseMessagingService
from core.messaging.types import (
    Message, MessageRecipient
)
from core.utils.exceptions import MessageValidationError

from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppMessagingService(BaseMessagingService):
    """WhatsApp implementation of messaging service"""

    def __init__(self, api_client: Any):
        """Initialize with WhatsApp API client"""
        self.api_client = api_client

    def _send_message(self, message: Message) -> Dict[str, Any]:
        """Send message through WhatsApp API"""
        try:
            # Convert core message to WhatsApp format
            whatsapp_message = WhatsAppMessage.from_core_message(message)

            # Send via API client
            response = self.api_client.send_message(whatsapp_message)

            return response
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise MessageValidationError(f"Failed to send message: {str(e)}")

    def send_template(
        self,
        recipient: MessageRecipient,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send template message through WhatsApp"""
        try:
            message = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient.channel_id.value,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": language
                }
            }

            if components:
                message["template"]["components"] = components

            return self.api_client.send_message(message)
        except Exception as e:
            logger.error(f"Error sending template {template_name}: {str(e)}")
            raise MessageValidationError(f"Failed to send template: {str(e)}")

    def get_template(self, template_name: str) -> Dict[str, Any]:
        """Get template from WhatsApp"""
        try:
            return self.api_client.get_template(template_name)
        except Exception as e:
            logger.error(f"Error getting template {template_name}: {str(e)}")
            raise MessageValidationError(f"Failed to get template: {str(e)}")

    def list_templates(self) -> List[Dict[str, Any]]:
        """List available WhatsApp templates"""
        try:
            return self.api_client.list_templates()
        except Exception as e:
            logger.error(f"Error listing templates: {str(e)}")
            raise MessageValidationError(f"Failed to list templates: {str(e)}")

    def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create WhatsApp template"""
        try:
            return self.api_client.create_template(template_data)
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            raise MessageValidationError(f"Failed to create template: {str(e)}")

    def delete_template(self, template_name: str) -> bool:
        """Delete WhatsApp template"""
        try:
            return self.api_client.delete_template(template_name)
        except Exception as e:
            logger.error(f"Error deleting template {template_name}: {str(e)}")
            raise MessageValidationError(f"Failed to delete template: {str(e)}")

    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get WhatsApp message status"""
        try:
            return self.api_client.get_message_status(message_id)
        except Exception as e:
            logger.error(f"Error getting message status: {str(e)}")
            raise MessageValidationError(f"Failed to get message status: {str(e)}")
