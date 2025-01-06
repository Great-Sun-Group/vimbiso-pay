"""WhatsApp messaging service implementation"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from core.messaging.base import BaseMessagingService
from core.messaging.exceptions import MessageValidationError
from core.messaging.types import (Button, InteractiveContent, InteractiveType,
                                  Message, MessageRecipient, TemplateContent,
                                  TextContent)
from core.utils.exceptions import SystemException
from decouple import config

from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppMessagingService(BaseMessagingService):
    """WhatsApp implementation of messaging service"""

    def __init__(self):
        """Initialize WhatsApp messaging service"""
        super().__init__()
        self.state_manager = None  # Will be set by MessagingService

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

        sections = []
        control_rows = []

        # Add any extra rows as a section if provided
        if extra_rows:
            # Ensure each row has required fields
            validated_rows = []
            for row in extra_rows:
                if "id" in row and "title" in row:
                    validated_row = {
                        "id": row["id"],
                        "title": row["title"]
                    }
                    if "description" in row:
                        validated_row["description"] = row["description"]
                    validated_rows.append(validated_row)

            if validated_rows:
                sections.append({
                    "title": "Actions",
                    "rows": validated_rows
                })

        # Add proceed option if requested
        if proceed_option:
            control_rows.append({
                "id": "Y",
                "title": "✅ Continue",
                "description": "Proceed with the current action"
            })

        # Add menu option if requested
        if include_menu:
            control_rows.append({
                "id": "X",
                "title": "🏡 Menu",
                "description": "Return to main menu"
            })

        # Add control section if we have control rows
        if control_rows:
            sections.append({
                "title": "Control",
                "rows": control_rows
            })

        # Build the message
        message_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel_identifier,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": message},
                "action": {
                    "button": f"🕹️ {navigate_is}",
                    "sections": sections
                }
            }
        }

        # Add footer if we have sections
        if sections:
            message_data["interactive"]["footer"] = {
                "text": "Choose an option from the list"
            }

        return message_data

    def send_whatsapp_message(self, payload: Dict, phone_number_id: Optional[str] = None) -> Dict:
        """Send message to WhatsApp Cloud API with detailed logging.

        Args:
            payload: Message payload in WhatsApp format
            phone_number_id: Optional phone number ID, defaults to config value

        Returns:
            Dict: API response

        Raises:
            SystemException: If message sending fails
        """
        # Log the request payload
        logger.info("WhatsApp request: %s", json.dumps({
            "payload": payload
        }, indent=2))

        try:
            # Check if we're in mock mode
            if hasattr(self, 'state_manager') and self.state_manager.get('mock_testing'):
                # Return mock success response
                response_data = {
                    "messaging_product": "whatsapp",
                    "contacts": [{
                        "input": payload.get("to"),
                        "wa_id": payload.get("to")
                    }],
                    "messages": [{
                        "id": f"mock_message_{datetime.utcnow().timestamp()}"
                    }]
                }
                logger.info("Mock WhatsApp response: %s", json.dumps(response_data, indent=2))
                return response_data

            # Real API call for non-mock mode
            phone_number_id = phone_number_id or config("WHATSAPP_PHONE_NUMBER_ID")
            api_url = config("WHATSAPP_API_URL", default="https://graph.facebook.com/v20.0/")
            url = f"{api_url}{phone_number_id}/messages"

            headers = {
                "Authorization": f"Bearer {config('WHATSAPP_ACCESS_TOKEN')}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, json=payload, headers=headers)

            # Log the complete response
            logger.info("WhatsApp response: %s", json.dumps(response.json(), indent=2))

            if response.status_code != 200:
                error_msg = f"WhatsApp API Error [{response.status_code}]: {response.text}"
                logger.error(error_msg)

                # Check for rate limit error
                response_data = response.json()
                if (response.status_code == 400 and response_data.get("error", {}).get("code") == 131056):
                    raise SystemException(
                        message=error_msg,
                        code="WHATSAPP_RATE_LIMIT",
                        service="whatsapp",
                        action="send_message"
                    )
                else:
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

            # Use class method to send message and get response
            response = self.send_whatsapp_message(whatsapp_message)

            # Verify WhatsApp accepted the message
            if not response.get("messages", []):
                logger.error("Message not accepted by WhatsApp: %s", response)
                raise SystemException(
                    message="Message not accepted by WhatsApp",
                    code="WHATSAPP_ACCEPTANCE_ERROR",
                    service="whatsapp",
                    action="send_message"
                )

            # Log successful acceptance
            message_id = response["messages"][0].get("id")
            logger.info("Message accepted by WhatsApp with ID: %s", message_id)

            # Add acceptance info to message
            message.metadata = {
                "whatsapp_message_id": message_id,
                "accepted_at": datetime.utcnow().isoformat()
            }

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
        buttons: Optional[List[Button]] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
        header: Optional[str] = None,
        footer: Optional[str] = None,
        button_text: Optional[str] = None,
    ) -> Message:
        """Send an interactive message

        Args:
            recipient: Message recipient
            body: Message body text
            buttons: Optional list of buttons for button type messages
            sections: Optional list of sections for list type messages
            header: Optional header text
            footer: Optional footer text
            button_text: Optional custom button text for list messages

        Returns:
            Message: Sent message
        """
        if buttons and sections:
            raise MessageValidationError(
                message="Cannot specify both buttons and sections",
                service="whatsapp",
                action="send_interactive",
                validation_details={
                    "error": "invalid_params",
                    "detail": "buttons and sections are mutually exclusive"
                }
            )

        interactive_type = InteractiveType.BUTTON if buttons else InteractiveType.LIST
        if buttons:
            message = Message(
                recipient=recipient,
                content=InteractiveContent(
                    interactive_type=interactive_type,
                    body=body,
                    buttons=buttons or [],
                    sections=[],  # Empty sections for button messages
                    header=header,
                    footer=footer
                )
            )
        elif sections:
            message = Message(
                recipient=recipient,
                content=InteractiveContent(
                    interactive_type=interactive_type,
                    body=body,
                    buttons=[],  # Empty buttons for list messages
                    sections=sections,
                    button_text=button_text or "Select",
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
