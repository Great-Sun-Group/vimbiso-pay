"""WhatsApp messaging service implementation"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from core.messaging.base import BaseMessagingService
from core.messaging.exceptions import MessageValidationError
from core.messaging.types import (Button, InteractiveContent, InteractiveType,
                                  Message, MessageRecipient, TemplateContent,
                                  TextContent)
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

    def _is_mock_mode(self) -> bool:
        """Check if service is in mock testing mode"""
        return hasattr(self, 'state_manager') and self.state_manager.is_mock_testing()

    def send_message(self, message: Message) -> Message:
        """Send a message through WhatsApp Cloud API or mock.

        This method:
        1. Converts core Message to WhatsApp format
        2. Determines if message should go to mock or real API
        3. Sends and processes response
        4. Updates message metadata

        Args:
            message: Core Message object to send

        Returns:
            Message: Sent message with metadata

        Raises:
            MessageValidationError: If message sending fails
        """
        try:
            # Convert message to WhatsApp format
            whatsapp_message = WhatsAppMessage.from_core_message(message)

            # Log basic info - full payload not needed since we're async
            logger.info("Sending %s message to %s",
                        message.content.type,
                        message.recipient.channel_id.value)

            # Send through appropriate handler
            handler = (
                self._handle_mock_send if self._is_mock_mode()
                else self._handle_production_send
            )
            return handler(message, whatsapp_message)

        except Exception as e:
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

    def _handle_mock_send(self, message: Message, whatsapp_message: Dict) -> Message:
        """Handle mock message sending path

        Args:
            message: Original core Message
            whatsapp_message: Converted WhatsApp format message

        Returns:
            Message: Message with mock metadata
        """
        logger.info("Mock mode: sending to mock server")

        try:
            # Send and wait for response
            response = requests.post(
                "http://mock:8001/bot/webhook",
                json=whatsapp_message,
                headers={"Content-Type": "application/json"},
                timeout=10  # Increased timeout
            )

            # Track when sent and response
            message.metadata = {
                "sent_at": datetime.utcnow().isoformat(),
                "mock": True,
                "status_code": response.status_code
            }

            # Try to parse response
            try:
                response_data = response.json()
                message.metadata["response"] = response_data
                logger.debug(f"Mock server response: {response_data}")

                # Check if response indicates success
                if response.status_code != 200 or not response_data.get("messaging_product"):
                    logger.error(f"Mock server error response: {response_data}")
                    raise MessageValidationError(
                        message="Mock server returned error response",
                        service="whatsapp",
                        action="send_message",
                        validation_details={
                            "status_code": response.status_code,
                            "response": response_data
                        }
                    )
            except Exception as e:
                message.metadata["response"] = response.text
                logger.error(f"Error parsing mock response: {str(e)}")
                raise MessageValidationError(
                    message=f"Failed to parse mock response: {str(e)}",
                    service="whatsapp",
                    action="send_message",
                    validation_details={
                        "status_code": response.status_code,
                        "response": response.text
                    }
                )

            return message

        except Exception as e:
            # Log error and include in metadata
            logger.warning("Mock server request failed: %s", e)
            message.metadata = {
                "sent_at": datetime.utcnow().isoformat(),
                "mock": True,
                "error": str(e)
            }
            return message

    def _handle_production_send(self, message: Message, whatsapp_message: Dict) -> Message:
        """Handle production message sending path

        Args:
            message: Original core Message
            whatsapp_message: Converted WhatsApp format message

        Returns:
            Message: Message with metadata
        """
        logger.info("Production mode: sending to WhatsApp")

        # Get API configuration
        phone_number_id = config("WHATSAPP_PHONE_NUMBER_ID")
        api_url = config("WHATSAPP_API_URL", default="https://graph.facebook.com/v20.0/")
        url = f"{api_url}{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {config('WHATSAPP_ACCESS_TOKEN')}",
            "Content-Type": "application/json",
        }

        try:
            # Send and wait for response
            response = requests.post(
                url,
                json=whatsapp_message,
                headers=headers,
                timeout=10  # Increased timeout
            )

            # Track when sent and response
            message.metadata = {
                "sent_at": datetime.utcnow().isoformat(),
                "status_code": response.status_code
            }

            # Try to parse response
            try:
                message.metadata["response"] = response.json()
            except Exception:
                message.metadata["response"] = response.text

            return message

        except Exception as e:
            # Log error and include in metadata
            logger.warning("WhatsApp API request failed: %s", e)
            message.metadata = {
                "sent_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            return message

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
