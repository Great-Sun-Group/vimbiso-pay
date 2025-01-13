"""Core messaging interface"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .exceptions import (MessageDeliveryError, MessageHandlerError,
                         MessageTemplateError, MessageValidationError)
from .types import Button, Message, MessageRecipient

__all__ = [
    'MessagingServiceInterface',
    'MessageDeliveryError',
    'MessageHandlerError',
    'MessageTemplateError',
    'MessageValidationError',
    'Button',
    'Message',
    'MessageRecipient',
]


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
        self,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send a text message

        The recipient will be injected from state by MessagingService.

        Args:
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
        body: str,
        buttons: Optional[List[Button]] = None,
        header: Optional[str] = None,
        footer: Optional[str] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
        button_text: Optional[str] = None
    ) -> Message:
        """Send an interactive message

        The recipient will be injected from state by MessagingService.

        Args:
            body: Message body text
            buttons: Optional buttons array for button type messages
            header: Optional header text
            footer: Optional footer text
            sections: Optional sections array for list type messages
            button_text: Optional button text for list type messages

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
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        """Send a template message

        The recipient will be injected from state by MessagingService.

        Args:
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

    @abstractmethod
    def handle_incoming_message(self, payload: Dict[str, Any]) -> None:
        """Handle incoming message from channel

        This method is responsible for:
        1. Extracting message data from channel-specific payload
        2. Converting to standard Message format
        3. Storing in state_manager.incoming_message

        Args:
            payload: Raw message payload from channel

        Raises:
            MessageValidationError: If message validation fails
            MessageHandlerError: If message handling fails
        """
        pass
