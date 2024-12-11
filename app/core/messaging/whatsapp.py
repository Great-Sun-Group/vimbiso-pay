import logging
from typing import Any, Dict, List, Optional

import requests
from decouple import config

from .base import BaseMessagingService
from .exceptions import (
    MessageDeliveryError,
    MessageTemplateError,
    TemplateNotFoundError,
    TemplateValidationError,
)
from .types import Message, MessageRecipient

logger = logging.getLogger(__name__)


class WhatsAppMessagingService(BaseMessagingService):
    """WhatsApp-specific implementation of messaging service"""

    def __init__(self):
        """Initialize WhatsApp messaging service"""
        super().__init__()
        self.api_url = config("WHATSAPP_API_URL")
        self.api_token = config("WHATSAPP_API_TOKEN")
        self.phone_number_id = config("WHATSAPP_PHONE_NUMBER_ID")

    def _send_message(self, message: Message) -> Dict[str, Any]:
        """Send message via WhatsApp API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "messaging_product": message.messaging_product,
                "recipient_type": message.recipient_type,
                "to": message.recipient.phone_number,
                **message.content
            }

            response = requests.post(
                f"{self.api_url}/{self.phone_number_id}/messages",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to send WhatsApp message: {error_msg}")
                raise MessageDeliveryError(f"Failed to send message: {error_msg}")

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Network error sending WhatsApp message: {str(e)}")
            raise MessageDeliveryError(f"Network error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error sending WhatsApp message")
            raise MessageDeliveryError(f"Unexpected error: {str(e)}")

    def get_template(self, template_name: str) -> Dict[str, Any]:
        """Get WhatsApp message template"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                f"{self.api_url}/{self.phone_number_id}/message_templates",
                headers=headers,
                params={"name": template_name}
            )

            if response.status_code != 200:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to get template: {error_msg}")
                raise TemplateNotFoundError(f"Template not found: {error_msg}")

            templates = response.json().get("data", [])
            if not templates:
                raise TemplateNotFoundError(f"Template '{template_name}' not found")

            return templates[0]

        except requests.RequestException as e:
            logger.error(f"Network error getting template: {str(e)}")
            raise MessageTemplateError(f"Network error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error getting template")
            raise MessageTemplateError(f"Unexpected error: {str(e)}")

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all WhatsApp message templates"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                f"{self.api_url}/{self.phone_number_id}/message_templates",
                headers=headers
            )

            if response.status_code != 200:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to list templates: {error_msg}")
                raise MessageTemplateError(f"Failed to list templates: {error_msg}")

            return response.json().get("data", [])

        except requests.RequestException as e:
            logger.error(f"Network error listing templates: {str(e)}")
            raise MessageTemplateError(f"Network error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error listing templates")
            raise MessageTemplateError(f"Unexpected error: {str(e)}")

    def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new WhatsApp message template"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{self.api_url}/{self.phone_number_id}/message_templates",
                headers=headers,
                json=template_data
            )

            if response.status_code != 201:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to create template: {error_msg}")
                raise TemplateValidationError(f"Failed to create template: {error_msg}")

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Network error creating template: {str(e)}")
            raise MessageTemplateError(f"Network error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error creating template")
            raise MessageTemplateError(f"Unexpected error: {str(e)}")

    def delete_template(self, template_name: str) -> bool:
        """Delete a WhatsApp message template"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            response = requests.delete(
                f"{self.api_url}/{self.phone_number_id}/message_templates",
                headers=headers,
                params={"name": template_name}
            )

            if response.status_code != 200:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to delete template: {error_msg}")
                return False

            return True

        except requests.RequestException as e:
            logger.error(f"Network error deleting template: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting template: {str(e)}")
            return False

    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get WhatsApp message status"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                f"{self.api_url}/{message_id}",
                headers=headers
            )

            if response.status_code != 200:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to get message status: {error_msg}")
                raise MessageDeliveryError(f"Failed to get message status: {error_msg}")

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Network error getting message status: {str(e)}")
            raise MessageDeliveryError(f"Network error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error getting message status")
            raise MessageDeliveryError(f"Unexpected error: {str(e)}")

    def send_template(
        self,
        recipient: MessageRecipient,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send a template message via WhatsApp"""
        message = Message(
            recipient=recipient,
            content={
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": language,
                    **({"components": components} if components else {})
                }
            }
        )
        return self.send_message(message)
