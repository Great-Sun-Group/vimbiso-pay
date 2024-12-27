"""WhatsApp bot service implementation"""
import logging
from typing import Any, Dict

from core.utils.state_validator import StateValidator
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

        # Validate initial state at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id"),
                "jwt_token": state_manager.get("jwt_token")
            },
            {"channel"}  # Only channel is required initially
        )
        if not validation.is_valid:
            raise ValueError(f"Invalid initial state: {validation.error_message}")

        # Initialize with validated state
        self.state_manager = state_manager
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Missing channel identifier")

        # Initialize handlers with state manager
        self.auth_handler = AuthActionHandler(state_manager)
        self.message_handler = MessageHandler(state_manager)

        # Process message with validation
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            self.response = WhatsAppMessage.create_text(
                channel["identifier"],
                f"Error: Invalid state - {validation.error_message}"
            )
        else:
            self.response = self.message_handler.process_message(payload)

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
