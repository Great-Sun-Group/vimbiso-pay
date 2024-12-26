"""WhatsApp bot service implementation"""
import logging
from typing import Dict, Any

from .base_handler import BaseActionHandler
from .types import BotServiceInterface, WhatsAppMessage
from .auth_handlers import AuthActionHandler
from .message_handler import MessageHandler

logger = logging.getLogger(__name__)


class CredexBotService(BotServiceInterface, BaseActionHandler):
    """WhatsApp bot service implementation"""

    def __init__(self, payload: Dict[str, Any], user: Any):
        """Initialize bot service"""
        BotServiceInterface.__init__(self, payload=payload, user=user)
        BaseActionHandler.__init__(self, self)

        # Log initial state
        logger.debug("Initializing bot service:")
        logger.debug(f"- User state: {user.state.state}")
        logger.debug(f"- Has jwt_token: {bool(user.state.jwt_token)}")

        # Initialize services and handlers
        self.credex_service = user.state.get_or_create_credex_service()
        self.credex_service._parent_service = self

        # Log service initialization
        logger.debug("Service initialization:")
        logger.debug(f"- Has credex_service: {bool(self.credex_service)}")
        logger.debug(f"- Parent service set: {bool(self.credex_service._parent_service == self)}")
        logger.debug(f"- Has jwt_token: {bool(self.credex_service._jwt_token)}")

        # Initialize handlers
        self.auth_handler = AuthActionHandler(self)
        self.message_handler = MessageHandler(self)

        # Log state before message processing
        logger.debug("State before message processing:")
        logger.debug(f"- User state: {user.state.state}")
        logger.debug(f"- Has jwt_token: {bool(user.state.jwt_token)}")

        # Process message
        self.response = self.message_handler.process_message()

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
