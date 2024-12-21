"""WhatsApp bot service implementation"""
import logging
from typing import Dict, Any

from .base_handler import BaseActionHandler
from .types import BotServiceInterface, WhatsAppMessage
from .auth_handlers import AuthActionHandler
from .message_handler import MessageHandler
from .state_manager import StateManager

logger = logging.getLogger(__name__)


class CredexBotService(BotServiceInterface, BaseActionHandler):
    """WhatsApp bot service implementation"""

    def __init__(self, payload: Dict[str, Any], user: Any):
        """Initialize bot service"""
        BotServiceInterface.__init__(self, payload=payload, user=user)
        BaseActionHandler.__init__(self, self)

        # Initialize services and handlers
        self.credex_service = user.state.get_or_create_credex_service()
        self.credex_service._parent_service = self
        self.auth_handler = AuthActionHandler(self)
        self.state_manager = StateManager()
        self.message_handler = MessageHandler(self)

        # Process message
        self.response = self.message_handler.process_message()

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
