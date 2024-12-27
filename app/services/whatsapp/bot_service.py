"""WhatsApp bot service implementation"""
import logging
from typing import Any, Dict

from . import auth_handlers as auth
from .handlers.message import message_handler
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

        # Initialize parent with payload and state manager
        super().__init__({"entry": [{"changes": [{"value": {
            "messages": [{"type": payload.get("type", ""), "text": {"body": payload.get("text", "")}}]
        }}]}]}, state_manager)

        try:
            # Handle message based on type
            if self.message_type == "text" and self.body.lower() == "hi":
                # Handle initial greeting
                success, data = auth.handle_hi(state_manager)
                self.response = (
                    auth.handle_action_menu(state_manager) if success
                    else auth.handle_action_register(state_manager, register=True)
                )
            else:
                # Handle other messages
                self.response = message_handler.process_message(
                    state_manager,
                    self.message_type,
                    self.body
                )
        except ValueError as e:
            # Handle errors consistently
            self.response = auth.handle_error(state_manager, "Bot service", e)

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
