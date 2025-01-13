"""Core messaging service that orchestrates channel-specific implementations

This service maintains the layered architecture:
1. Core messaging module defines interfaces
2. Channel services implement specific channels
3. MessagingService orchestrates which implementation to use
"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.base import BaseMessagingService
from core.messaging.types import (
    Button, InteractiveContent, InteractiveType, Message, MessageRecipient,
    TemplateContent, TextContent
)

logger = logging.getLogger(__name__)


class MessagingService:
    """Core messaging service that orchestrates channel implementations"""

    def __init__(self, channel_service: BaseMessagingService, state_manager: Optional[any] = None):
        """Initialize messaging service with channel implementation

        Args:
            channel_service: Channel-specific messaging service that implements BaseMessagingService
            state_manager: Optional state manager instance
        """
        # Validate channel service implements base interface
        if not isinstance(channel_service, BaseMessagingService):
            raise ValueError(
                f"Channel service must implement BaseMessagingService, got {type(channel_service)}"
            )

        self.channel_service = channel_service
        self.state_manager = state_manager
        if state_manager:
            # Set up bidirectional relationships
            self.channel_service.state_manager = state_manager  # Give channel service access to state
            state_manager.messaging = self  # Keep wrapper as messaging interface

            # Ensure channel service can check mock testing state
            if hasattr(channel_service, 'set_mock_testing'):
                channel_service.set_mock_testing(state_manager.is_mock_testing())

    def send_message(self, message: Message) -> Message:
        """Send message through appropriate channel service"""
        return self.channel_service.send_message(message)

    def _get_recipient(self) -> MessageRecipient:
        """Get recipient from state"""
        if not self.state_manager:
            raise ValueError("No state manager available")

        channel_type = self.state_manager.get_channel_type()
        channel_id = self.state_manager.get_channel_id()

        return MessageRecipient(
            type=channel_type,
            identifier=channel_id
        )

    def _inject_recipient(self, message: Message) -> Message:
        """Inject recipient into message if not present"""
        if not message.recipient and self.state_manager:
            message.recipient = self._get_recipient()
        return message

    def send_text(
        self,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send text message through appropriate channel service

        Gets recipient from state automatically.

        Args:
            text: Text content to send
            preview_url: Whether to show URL previews

        Returns:
            Message: Sent message with delivery details
        """
        # Create message with just content
        message = Message(
            content=TextContent(body=text, preview_url=preview_url)
        )

        # Inject recipient and send
        message = self._inject_recipient(message)
        return self.channel_service.send_message(message)

    def send_interactive(
        self,
        body: str,
        buttons: Optional[List[Button]] = None,
        header: Optional[str] = None,
        footer: Optional[str] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
        button_text: Optional[str] = None
    ) -> Message:
        """Send interactive message through appropriate channel service

        Gets recipient from state automatically.

        Args:
            body: Message body text
            buttons: Optional interactive buttons
            header: Optional header text
            footer: Optional footer text
            sections: Optional list sections
            button_text: Optional custom button text

        Returns:
            Message: Sent message with delivery details
        """
        # Create message with just content
        message = Message(
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON if buttons else InteractiveType.LIST,
                body=body,
                buttons=buttons or [],
                sections=sections or [],
                header=header,
                footer=footer,
                button_text=button_text
            )
        )

        # Inject recipient and send
        message = self._inject_recipient(message)
        return self.channel_service.send_message(message)

    def send_template(
        self,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        """Send template message through appropriate channel service

        Gets recipient from state automatically.

        Args:
            template_name: Name of template to use
            language: Language parameters
            components: Optional template components

        Returns:
            Message: Sent message with delivery details
        """
        # Create message with just content
        message = Message(
            content=TemplateContent(
                name=template_name,
                language=language,
                components=components or []
            )
        )

        # Inject recipient and send
        message = self._inject_recipient(message)
        return self.channel_service.send_message(message)

    def handle_incoming_message(self, payload: Dict[str, Any]) -> None:
        """Handle incoming message through appropriate channel service"""
        return self.channel_service.handle_incoming_message(payload)
