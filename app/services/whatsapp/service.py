"""WhatsApp messaging service implementation"""
import logging
from typing import Any, Dict, List, Optional, Union

from core.messaging.base import BaseMessagingService
from core.messaging.types import (
    AudioContent, Button, DocumentContent, ImageContent,
    Message, MessageRecipient, VideoContent
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
            # Create template message
            message = Message(
                recipient=recipient,
                content={
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": language,
                        "components": components or []
                    }
                }
            )
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending template {template_name}: {str(e)}")
            raise MessageValidationError(f"Failed to send template: {str(e)}")

    def send_interactive(
        self,
        recipient: MessageRecipient,
        body: str,
        buttons: List[Button],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send interactive message through WhatsApp"""
        try:
            # Create interactive message
            message = Message(
                recipient=recipient,
                content={
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": body},
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {
                                        "id": btn.id,
                                        "title": btn.title[:20]  # WhatsApp limit
                                    }
                                }
                                for btn in buttons
                            ]
                        }
                    }
                }
            )
            if header:
                message.content["interactive"]["header"] = {
                    "type": "text",
                    "text": header
                }
            if footer:
                message.content["interactive"]["footer"] = {
                    "text": footer
                }
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending interactive message: {str(e)}")
            raise MessageValidationError(f"Failed to send interactive message: {str(e)}")

    def send_media(
        self,
        recipient: MessageRecipient,
        content: Union[ImageContent, DocumentContent, AudioContent, VideoContent],
    ) -> Dict[str, Any]:
        """Send media message through WhatsApp"""
        try:
            # Create media message
            message = Message(
                recipient=recipient,
                content={
                    "type": content.type,
                    content.type.value: {
                        "link": content.url,
                        **({"caption": content.caption} if content.caption else {}),
                        **({"filename": content.filename} if content.filename else {})
                    }
                }
            )
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending media message: {str(e)}")
            raise MessageValidationError(f"Failed to send media message: {str(e)}")

    def send_location(
        self,
        recipient: MessageRecipient,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send location message through WhatsApp"""
        try:
            # Create location message
            message = Message(
                recipient=recipient,
                content={
                    "type": "location",
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude,
                        **({"name": name} if name else {}),
                        **({"address": address} if address else {})
                    }
                }
            )
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending location message: {str(e)}")
            raise MessageValidationError(f"Failed to send location message: {str(e)}")

    def authenticate_user(self, channel_type: str, channel_id: str) -> Dict[str, Any]:
        """Authenticate user with phone number"""
        try:
            # Attempt authentication through API
            response = self.api_client.authenticate_user(phone=channel_id)
            return response
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            raise MessageValidationError(f"Failed to authenticate: {str(e)}")

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
