"""Core messaging service that orchestrates channel-specific implementations

This service maintains the layered architecture:
1. Core messaging module defines interfaces
2. Channel services implement specific channels
3. MessagingService orchestrates which implementation to use
"""
import logging
from typing import Optional

from core.messaging.base import BaseMessagingService
from core.messaging.types import Message

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
        if state_manager:
            self.channel_service.state_manager = state_manager

    def handle_message(self) -> Message:
        """Handle incoming message through appropriate channel service"""
        return self.channel_service.handle_message()

    def send_message(self, message: Message) -> Message:
        """Send message through appropriate channel service"""
        return self.channel_service.send_message(message)
