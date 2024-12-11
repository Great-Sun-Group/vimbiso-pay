import logging
from typing import Any, Dict, List, Optional, Union

from .exceptions import (
    InvalidMessageTypeError,
    InvalidRecipientError,
    MessageFormatError,
    MessageValidationError,
)
from .interface import MessagingServiceInterface
from .types import (
    AudioContent,
    Button,
    DocumentContent,
    ImageContent,
    Message,
    MessageRecipient,
    MessageType,
    VideoContent,
)

logger = logging.getLogger(__name__)


class BaseMessagingService(MessagingServiceInterface):
    """Base class implementing common messaging functionality"""

    def send_message(self, message: Message) -> Dict[str, Any]:
        """Send a message to a recipient"""
        if not self.validate_message(message):
            raise MessageValidationError("Invalid message")

        return self._send_message(message)

    def send_text(
        self, recipient: MessageRecipient, text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        """Send a text message"""
        if not text:
            raise MessageFormatError("Text content cannot be empty")

        message = Message(
            recipient=recipient,
            content={
                "type": MessageType.TEXT,
                "text": {"body": text},
                "preview_url": preview_url
            }
        )
        return self.send_message(message)

    def send_interactive(
        self,
        recipient: MessageRecipient,
        body: str,
        buttons: List[Button],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an interactive message"""
        if not body:
            raise MessageFormatError("Message body cannot be empty")
        if not buttons:
            raise MessageFormatError("Interactive message must have buttons")

        message = Message(
            recipient=recipient,
            content={
                "type": MessageType.INTERACTIVE,
                "interactive": {
                    "type": "button",
                    "body": {"text": body},
                    "action": {
                        "buttons": [
                            {"type": btn.type, "reply": {"id": btn.id, "title": btn.title}}
                            for btn in buttons
                        ]
                    }
                }
            }
        )

        if header:
            message.content["interactive"]["header"] = {"type": "text", "text": header}
        if footer:
            message.content["interactive"]["footer"] = {"text": footer}

        return self.send_message(message)

    def send_media(
        self,
        recipient: MessageRecipient,
        content: Union[ImageContent, DocumentContent, AudioContent, VideoContent],
    ) -> Dict[str, Any]:
        """Send a media message"""
        if not content.url:
            raise MessageFormatError("Media URL is required")

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

    def send_location(
        self,
        recipient: MessageRecipient,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a location message"""
        message = Message(
            recipient=recipient,
            content={
                "type": MessageType.LOCATION,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    **({"name": name} if name else {}),
                    **({"address": address} if address else {})
                }
            }
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
        if not recipient.phone_number:
            raise InvalidRecipientError("Recipient phone number is required")

    def _validate_content(self, content: Dict[str, Any]) -> None:
        """Validate message content"""
        if not content or "type" not in content:
            raise MessageFormatError("Message content must have a type")

        try:
            message_type = MessageType(content["type"])
        except ValueError:
            raise InvalidMessageTypeError(f"Invalid message type: {content['type']}")

        # Additional type-specific validation can be added here
        if message_type == MessageType.TEXT and (
            "text" not in content or "body" not in content["text"]
        ):
            raise MessageFormatError("Text message must have a body")

    def _send_message(self, message: Message) -> Dict[str, Any]:
        """Internal method to send the message

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Messaging provider must implement _send_message method"
        )
