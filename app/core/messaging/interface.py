"""Core messaging interface"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .exceptions import (  # noqa: F401
    MessageDeliveryError,
    MessageHandlerError,
    MessageTemplateError,
    MessageValidationError
)
from .types import (
    Button,
    Message,
    MessageRecipient,
)


class MessagingServiceInterface(ABC):
    """Interface defining core messaging operations"""

    @abstractmethod
    def send_message(self, message: Message) -> Message:
        """Send a message to a recipient

        Args:
            message: Message to send

        Returns:
            Sent message with delivery details

        Raises:
            MessageValidationError: If message validation fails
            MessageDeliveryError: If message delivery fails
            MessageHandlerError: If message handling fails
        """
        pass

    @abstractmethod
    def send_text(
        self, recipient: MessageRecipient, text: str, preview_url: bool = False
    ) -> Message:
        """Send a text message

        Args:
            recipient: Message recipient
            text: Text content
            preview_url: Whether to show URL previews

        Returns:
            Sent message with delivery details

        Raises:
            MessageValidationError: If message validation fails
            MessageDeliveryError: If message delivery fails
            MessageHandlerError: If message handling fails
        """
        pass

    @abstractmethod
    def send_interactive(
        self,
        recipient: MessageRecipient,
        body: str,
        buttons: List[Button],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Message:
        """Send an interactive message

        Args:
            recipient: Message recipient
            body: Message body text
            buttons: Interactive buttons
            header: Optional header text
            footer: Optional footer text

        Returns:
            Sent message with delivery details

        Raises:
            MessageValidationError: If message validation fails
            MessageDeliveryError: If message delivery fails
            MessageHandlerError: If message handling fails
        """
        pass

    @abstractmethod
    def send_template(
        self,
        recipient: MessageRecipient,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """Send a template message

        Args:
            recipient: Message recipient
            template_name: Name of template to use
            language: Language parameters
            components: Optional template components

        Returns:
            Sent message with delivery details

        Raises:
            MessageValidationError: If message validation fails
            MessageDeliveryError: If message delivery fails
            MessageTemplateError: If template processing fails
            MessageHandlerError: If message handling fails
        """
        pass

    @abstractmethod
    def validate_message(self, message: Message) -> bool:
        """Validate a message before sending

        Args:
            message: Message to validate

        Returns:
            True if valid, False otherwise

        Raises:
            MessageValidationError: If validation fails with details
        """
        pass
