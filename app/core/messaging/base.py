"""Base messaging service

This module provides the base messaging service that implements common functionality
and enforces the messaging service interface.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from .interface import MessagingServiceInterface
from .types import Button, Message, MessageRecipient


class BaseMessagingService(MessagingServiceInterface):
    """Base class for messaging services

    This class:
    1. Implements common functionality
    2. Enforces the messaging service interface
    3. Provides hooks for channel-specific implementations
    """

    def __init__(self):
        """Initialize base messaging service"""
        self.state_manager = None

    @abstractmethod
    def send_message(self, message: Message) -> Message:
        """Send a message through the channel

        Args:
            message: Message to send

        Returns:
            Sent message with delivery details
        """
        pass

    @abstractmethod
    def send_text(
        self,
        recipient: MessageRecipient,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send a text message

        Args:
            recipient: Message recipient
            text: Text content
            preview_url: Whether to show URL previews

        Returns:
            Sent message with delivery details
        """
        pass

    @abstractmethod
    def send_interactive(
        self,
        recipient: MessageRecipient,
        body: str,
        buttons: Optional[List[Button]] = None,
        header: Optional[str] = None,
        footer: Optional[str] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
        button_text: Optional[str] = None,
    ) -> Message:
        """Send an interactive message

        Args:
            recipient: Message recipient
            body: Message body text
            buttons: Optional interactive buttons
            header: Optional header text
            footer: Optional footer text
            sections: Optional list sections
            button_text: Optional custom button text

        Returns:
            Sent message with delivery details
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
        """
        pass

    def validate_message(self, message: Message) -> bool:
        """Validate a message before sending

        Args:
            message: Message to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic validation - subclasses can override for channel-specific validation
        if not message.recipient:
            return False
        if not message.content:
            return False
        return True
