"""WhatsApp messaging service implementation"""
import json
import logging
from typing import Any, Dict, List, Optional

import requests
from decouple import config
from core.messaging.base import BaseMessagingService
from core.messaging.exceptions import MessageValidationError
from core.messaging.types import (Button, InteractiveContent, InteractiveType,
                                  Message, MessageRecipient, TemplateContent,
                                  TextContent)
from core.utils.exceptions import SystemException

from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppMessagingService(BaseMessagingService):
    """WhatsApp implementation of messaging service"""

    @classmethod
    def wrap_text(
        cls,
        message: str,
        channel_identifier: str,  # Channel identifier from state as SINGLE SOURCE OF TRUTH
        proceed_option: bool = False,
        x_is_menu: bool = False,
        navigate_is: str = "Respond",
        extra_rows: List = [],
        use_buttons: bool = False,
        yes_or_no: bool = False,
        custom: Dict = dict(),
        plain: bool = False,
        include_menu: bool = True,
    ) -> Dict:
        """Wrap text message with WhatsApp formatting

        Args:
            message: Text message to wrap
            channel_identifier: Channel identifier from state (e.g. WhatsApp number)
            proceed_option: Whether to include proceed option
            x_is_menu: Whether X button is menu
            navigate_is: Navigation button text
            extra_rows: Additional row options
            use_buttons: Whether to use button format
            yes_or_no: Whether to show yes/no buttons
            custom: Custom button configuration
            plain: Whether to use plain text format
            include_menu: Whether to include menu option

        Returns:
            Dict: Formatted WhatsApp message
        """
        logger.debug(f"Wrapping text message: {message}")
        if use_buttons:
            rows = [
                {"type": "reply", "reply": {"id": "N", "title": "❌ No"}},
                {"type": "reply", "reply": {"id": "Y", "title": "✅ Yes"}},
            ]
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel_identifier,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": message},
                    "action": {
                        "buttons": (
                            [
                                {
                                    "type": "reply",
                                    "reply": (
                                        custom
                                        if custom
                                        else {
                                            "id": "X",
                                            "title": (
                                                "🏡 Menu" if x_is_menu else "❌ Cancel"
                                            ),
                                        }
                                    ),
                                }
                            ]
                            if not yes_or_no
                            else rows
                        )
                    },
                },
            }

        if len(message) > 1024 or plain:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel_identifier,
                "type": "text",
                "text": {"body": message},
            }

        rows = extra_rows

        if proceed_option:
            rows.append({"id": "Y", "title": "✅ Continue"})

        if include_menu:
            rows.append({"id": "X", "title": "🏡 Menu"})

        row_data = []
        keystore = []
        for row in rows:
            if row.get("id") not in keystore:
                row_data.append(row)
                keystore.append(row.get("id"))

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel_identifier,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": message},
                "action": {
                    "button": f"🕹️ {navigate_is}",
                    "sections": [{"title": "Control", "rows": row_data}],
                },
            },
        }

    @classmethod
    def send_whatsapp_message(cls, payload: Dict, phone_number_id: Optional[str] = None) -> Dict:
        """Send message to WhatsApp Cloud API with detailed logging.

        Args:
            payload: Message payload in WhatsApp format
            phone_number_id: Optional phone number ID, defaults to config value

        Returns:
            Dict: API response

        Raises:
            SystemException: If message sending fails
        """
        # Get configuration
        phone_number_id = phone_number_id or config("WHATSAPP_PHONE_NUMBER_ID")
        api_url = config("WHATSAPP_API_URL", default="https://graph.facebook.com/v20.0/")
        url = f"{api_url}{phone_number_id}/messages"

        headers = {
            "Authorization": f"Bearer {config('WHATSAPP_ACCESS_TOKEN')}",
            "Content-Type": "application/json",
        }

        # Log the exact request we're sending
        logger.info("WhatsApp request: %s", json.dumps({
            "url": url,
            "headers": {k: v for k, v in headers.items() if k != "Authorization"},
            "payload": payload
        }, indent=2))

        try:
            response = requests.post(url, json=payload, headers=headers)

            # Log the complete response
            logger.info("WhatsApp response: %s", json.dumps(response.json(), indent=2))

            if response.status_code != 200:
                error_msg = f"WhatsApp API Error [{response.status_code}]: {response.text}"
                logger.error(error_msg)
                raise SystemException(
                    message=error_msg,
                    code="WHATSAPP_API_ERROR",
                    service="whatsapp",
                    action="send_message"
                )
            return response.json()

        except requests.RequestException as e:
            error_msg = f"Error sending WhatsApp message: {str(e)}"
            logger.error(error_msg)
            raise SystemException(
                message=error_msg,
                code="WHATSAPP_REQUEST_ERROR",
                service="whatsapp",
                action="send_message"
            )
        except Exception as e:
            error_msg = f"Unexpected error sending WhatsApp message: {str(e)}"
            logger.error(error_msg)
            raise SystemException(
                message=error_msg,
                code="WHATSAPP_UNEXPECTED_ERROR",
                service="whatsapp",
                action="send_message"
            )

    def _send_message(self, message: Message) -> Message:
        """Internal method to send the message through WhatsApp API"""
        try:
            # Convert core Message to WhatsApp Cloud API format
            whatsapp_message = WhatsAppMessage.from_core_message(message)

            # Use class method to send message
            self.send_whatsapp_message(whatsapp_message)

            return message

        except SystemException as e:
            logger.error(f"Error sending message: {str(e)}")
            raise MessageValidationError(
                message=f"Failed to send message: {str(e)}",
                service="whatsapp",
                action="send_message",
                validation_details={
                    "error": str(e),
                    "message_type": message.content.type if message and message.content else None
                }
            )

    def send_text(
        self,
        recipient: MessageRecipient,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send a text message"""
        # Validate text content
        if not isinstance(text, str):
            raise MessageValidationError(
                message="Invalid text content type",
                service="whatsapp",
                action="send_text",
                validation_details={
                    "error": "invalid_type",
                    "expected": "str",
                    "received": type(text).__name__
                }
            )

        # Create message with validated content
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
            raise MessageValidationError(
                message=f"Failed to send template: {str(e)}",
                service="whatsapp",
                action="send_template",
                validation_details={
                    "error": str(e),
                    "template_name": template_name,
                    "language": language
                }
            )
