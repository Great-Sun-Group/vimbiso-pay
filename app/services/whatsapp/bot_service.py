"""WhatsApp bot service implementation"""
import logging
from typing import Any, Dict

from .auth_handlers import AuthActionHandler
from .handlers.message.message_handler import MessageHandler
from .types import BotServiceInterface, WhatsAppMessage

logger = logging.getLogger(__name__)


class CredexBotService(BotServiceInterface):
    """WhatsApp bot service implementation"""

    def __init__(self, payload: Dict[str, Any], state_manager: Any):
        """Initialize bot service with state manager

        Args:
            payload: Message payload
            state_manager: State manager instance
        """
        if not state_manager:
            raise ValueError("State manager is required")

        # Validate channel at initial boundary (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Missing channel identifier")

        # Initialize with validated channel
        self.state_manager = state_manager

        # Initialize handlers with state manager
        self.auth_handler = AuthActionHandler(state_manager)
        self.message_handler = MessageHandler(state_manager)

        # Set auth handler in message handler
        self.message_handler.auth_handler = self.auth_handler

        # Extract message type and text
        message_type = payload.get("type", "")
        message_text = payload.get("text", "")

        # Handle initial greeting
        if message_type == "text" and message_text.lower() == "hi":
            try:
                # Attempt login
                success, data = self.auth_handler.auth_flow.attempt_login()
                if success:
                    self.response = self.auth_handler.handle_action_menu()
                else:
                    self.response = self.auth_handler.handle_action_register(register=True)
            except ValueError as e:
                self.response = WhatsAppMessage.create_text(
                    channel["identifier"],
                    f"Error: {str(e)}"
                )
        else:
            self.response = self.message_handler.process_message(message_type, message_text)

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
