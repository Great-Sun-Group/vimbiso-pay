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

    def send_message(self, message: Message) -> Message:
        """Send a message to a recipient"""
        if not self.validate_message(message):
            raise MessageValidationError("Invalid message")

        return self._send_message(message)

    def send_text(
        self, recipient: MessageRecipient, text: str, preview_url: bool = False
    ) -> Message:
        """Send a text message"""
        if not text:
            raise MessageFormatError("Text content cannot be empty")

        message = Message(
            recipient=recipient,
            content=TextContent(body=text)
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
            raise MessageFormatError("Message body cannot be empty")
        if not buttons:
            raise MessageFormatError("Interactive message must have buttons")

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
        if not isinstance(content, MessageContent):
            raise MessageFormatError("Invalid message content type")

        if not content.type:
            raise MessageFormatError("Message content must have a type")

        # Type-specific validation is handled by the content classes

    def _send_message(self, message: Message) -> Message:
        """Internal method to send the message

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Messaging provider must implement _send_message method"
        )
