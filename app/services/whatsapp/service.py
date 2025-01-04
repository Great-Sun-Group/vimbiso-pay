"""WhatsApp messaging service implementation"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.base import BaseMessagingService
from core.messaging.exceptions import MessageValidationError
from core.messaging.types import (
    Button, InteractiveType, Message, MessageRecipient,
    TextContent, InteractiveContent, TemplateContent
)

from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppMessagingService(BaseMessagingService):
    """WhatsApp implementation of messaging service"""

    def send_message(self, message: Message) -> Message:
        """Send a message to a recipient"""
        try:
            # Convert to WhatsApp format for API (but keep original message)
            WhatsAppMessage.from_core_message(message)  # Validates message can be sent
            return message

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise MessageValidationError(f"Failed to send message: {str(e)}")

    def send_text(
        self,
        recipient: MessageRecipient,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send a text message"""
        message = Message(
            recipient=recipient,
            content=TextContent(body=text, preview_url=preview_url)
        )
        return self.send_message(message)

    def send_interactive(
        self,
        recipient: MessageRecipient,
        body: str,
        buttons: List[Button],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Message:
        """Send an interactive message"""
        message = Message(
            recipient=recipient,
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=body,
                buttons=buttons,
                header=header,
                footer=footer
            )
        )
        return self.send_message(message)

    def send_template(
        self,
        recipient: MessageRecipient,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """Send template message through WhatsApp"""
        try:
            # Create template message with proper content type
            message = Message(
                recipient=recipient,
                content=TemplateContent(
                    name=template_name,
                    language=language,
                    components=components or []
                )
            )
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending template {template_name}: {str(e)}")
            raise MessageValidationError(f"Failed to send template: {str(e)}")
