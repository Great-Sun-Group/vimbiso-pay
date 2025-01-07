"""Base messaging service implementation"""
import logging
from typing import List, Optional

from .exceptions import (
    InvalidMessageTypeError,
    InvalidRecipientError,
    MessageFormatError,
    MessageValidationError,
)
from .interface import MessagingServiceInterface
from .types import (
    Button,
    InteractiveContent,
    InteractiveType,
    Message,
    MessageContent,
    MessageRecipient,
    TextContent,
)

logger = logging.getLogger(__name__)


class BaseMessagingService(MessagingServiceInterface):
    """Base class implementing common messaging functionality"""

    def __init__(self):
        """Initialize base messaging service"""
        self.state_manager = None

    def _validate_state_manager(self) -> None:
        """Validate state manager is set and accessible"""
        if not self.state_manager:
            raise MessageValidationError(
                message="State manager not initialized",
                service="messaging",
                action="validate_state",
                validation_details={"error": "missing_state_manager"}
            )

    def _is_mock_mode(self) -> bool:
        """Check if service is in mock testing mode"""
        return self.state_manager and self.state_manager.get('mock_testing')

    def send_message(self, message: Message) -> Message:
        """Send a message to a recipient"""
        # Validate state manager first
        self._validate_state_manager()

        # Then validate message
        if not self.validate_message(message):
            raise MessageValidationError(
                message="Invalid message",
                service="messaging",
                action="send_message",
                validation_details={
                    "message_type": message.content.type if message and message.content else None,
                    "validation_error": "Message validation failed"
                }
            )

        return self._send_message(message)

    def send_text(
        self, recipient: MessageRecipient, text: str, preview_url: bool = False
    ) -> Message:
        """Send a text message"""
        if not text:
            raise MessageFormatError(
                message="Text content cannot be empty",
                service="messaging",
                action="send_text",
                format_details={"field": "text", "error": "empty"}
            )

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
        if not body:
            raise MessageFormatError(
                message="Message body cannot be empty",
                service="messaging",
                action="send_interactive",
                format_details={"field": "body", "error": "empty"}
            )
        if not buttons:
            raise MessageFormatError(
                message="Interactive message must have buttons",
                service="messaging",
                action="send_interactive",
                format_details={"field": "buttons", "error": "empty"}
            )

        content = InteractiveContent(
            interactive_type=InteractiveType.BUTTON,
            body=body,
            buttons=buttons,
            header=header,
            footer=footer
        )
        message = Message(
            recipient=recipient,
            content=content
        )

        return self.send_message(message)

    def validate_message(self, message: Message) -> bool:
        """Validate a message before sending"""
        try:
            self._validate_recipient(message.recipient)
            self._validate_content(message.content)
            return True
        except (InvalidRecipientError, InvalidMessageTypeError, MessageFormatError) as e:
            logger.warning(f"Message validation failed: {str(e)}")
            return False

    def _validate_recipient(self, recipient: MessageRecipient) -> None:
        """Validate recipient information"""
        if not recipient.channel_id:
            raise InvalidRecipientError("Channel identifier is required")
        if not recipient.channel_id.value:
            raise InvalidRecipientError("Channel identifier value is required")

    def _validate_content(self, content: MessageContent) -> None:
        """Validate message content"""
        # Validate content is a MessageContent instance
        if not isinstance(content, MessageContent):
            raise MessageFormatError(
                message="Invalid message content type",
                service="messaging",
                action="validate_content",
                format_details={
                    "expected": "MessageContent",
                    "received": type(content).__name__
                }
            )

        # Validate content has a type
        if not hasattr(content, 'type'):
            raise MessageFormatError(
                message="Message content must have a type field",
                service="messaging",
                action="validate_content",
                format_details={"error": "missing_type_field"}
            )

        # Validate type is set
        if not content.type:
            raise MessageFormatError(
                message="Message content must have a type value",
                service="messaging",
                action="validate_content",
                format_details={"error": "missing_type_value"}
            )

        # Type-specific validation
        if isinstance(content, TextContent):
            if not hasattr(content, 'body') or not content.body:
                raise MessageFormatError(
                    message="Text content must have a body",
                    service="messaging",
                    action="validate_content",
                    format_details={"error": "missing_body"}
                )
            if not isinstance(content.body, str):
                raise MessageFormatError(
                    message="Text content body must be a string",
                    service="messaging",
                    action="validate_content",
                    format_details={
                        "error": "invalid_body_type",
                        "expected": "str",
                        "received": type(content.body).__name__
                    }
                )

    def _send_message(self, message: Message) -> Message:
        """Internal method to send the message

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Messaging provider must implement _send_message method"
        )
