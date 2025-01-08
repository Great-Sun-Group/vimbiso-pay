"""Core messaging service that orchestrates channel-specific implementations

This service maintains the layered architecture:
1. Core messaging module defines interfaces
2. Channel services implement specific channels
3. MessagingService orchestrates which implementation to use
"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.base import BaseMessagingService
from core.messaging.types import Button, Message, MessageRecipient

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
            # Set up bidirectional relationship
            self.channel_service.state_manager = state_manager
            state_manager.messaging = self

    def send_message(self, message: Message) -> Message:
        """Send message through appropriate channel service"""
        return self.channel_service.send_message(message)

    def send_text(
        self,
        recipient: MessageRecipient,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send text message through appropriate channel service"""
        return self.channel_service.send_text(recipient, text, preview_url)

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
        """Send interactive message through appropriate channel service"""
        return self.channel_service.send_interactive(
            recipient,
            body,
            buttons,
            header=header,
            footer=footer,
            sections=sections,
            button_text=button_text
        )

    def send_template(
        self,
        recipient: MessageRecipient,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """Send template message through appropriate channel service"""
        return self.channel_service.send_template(
            recipient,
            template_name,
            language,
            components
        )
