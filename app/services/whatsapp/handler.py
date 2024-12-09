"""
WhatsApp bot service implementation.
Handles message routing and bot interactions.
"""
import logging
from typing import Dict, Any, Optional

from core.utils.exceptions import InvalidInputException
from core.utils.error_handler import error_decorator
from core.config.constants import CachedUser, get_greeting
from services.credex.service import CredExService
from .types import BotServiceInterface, WhatsAppMessage
from .account_handlers import AccountActionHandler
from .auth_handlers import AuthActionHandler
from .credex_handlers import CredexActionHandler

logger = logging.getLogger(__name__)


class CredexBotService(BotServiceInterface):
    """Service for handling WhatsApp bot interactions"""

    def __init__(self, payload: Dict[str, Any], user: CachedUser) -> None:
        """Initialize the bot service.

        Args:
            payload: Message payload from WhatsApp
            user: CachedUser instance
        """
        logger.debug(f"Initializing CredexBotService with payload: {payload}")
        if user is None:
            logger.error("User object is required")
            raise InvalidInputException("User object is required")

        # Initialize base service
        super().__init__(payload, user)
        logger.debug(f"Message type: {self.message_type}")
        logger.debug(f"Message body: {self.body}")
        logger.debug(f"Current state: {self.current_state}")

        # Initialize handlers and services
        self.credex_service = CredExService()
        self.action_handler = WhatsAppActionHandler(self)

        # Initialize state if empty
        if not self.current_state:
            logger.debug("Initializing empty state")
            self.state.update_state(
                state={},
                stage="handle_action_menu",
                update_from="init",
                option="handle_action_menu",
                direction="OUT"
            )
            self.current_state = self.state.get_state(self.user)

        self.response = self.handle()
        logger.debug(f"Final response: {self.response}")

    def refresh(self, reset: bool = True, silent: bool = True) -> Optional[str]:
        """Refresh user profile and state information.

        Args:
            reset: Whether to reset state
            silent: Whether to suppress notifications

        Returns:
            Optional[str]: Error message if any
        """
        return self.credex_service.refresh_member_info(
            phone=self.user.mobile_number,
            reset=reset,
            silent=silent
        )

    @error_decorator
    def handle(self) -> Dict[str, Any]:
        """Process the incoming message and generate response.

        Returns:
            Dict[str, Any]: Response message
        """
        logger.info(f"Entry point: {self.state.stage}")

        # Handle greeting messages
        if self.message_type == "text" and self.body.lower() in ["hi", "hello", "hey"]:
            greeting = get_greeting(self.user.first_name)
            self.state.update_state(
                state=self.current_state,
                stage="handle_action_menu",
                update_from="greeting",
                option="handle_action_menu"
            )
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.user.mobile_number,
                "type": "text",
                "text": {"body": greeting}
            }

        return self.action_handler.handle_action(self.state.stage)


class WhatsAppActionHandler:
    """Main handler for WhatsApp actions"""

    def __init__(self, service: CredexBotService):
        """Initialize handlers

        Args:
            service: Service instance for handling bot interactions
        """
        self.service = service
        self.auth_handler = AuthActionHandler(service)
        self.credex_handler = CredexActionHandler(service)
        self.account_handler = AccountActionHandler(service)

    def handle_action(self, action: str) -> WhatsAppMessage:
        """Route action to appropriate handler

        Args:
            action: Action to handle

        Returns:
            WhatsAppMessage: Response message
        """
        # Authentication and menu actions
        if action in ["handle_action_register", "handle_action_menu"]:
            return self._handle_auth_action(action)

        # Credex-related actions
        if action in [
            "handle_action_offer_credex",
            "handle_action_pending_offers_in",
            "handle_action_pending_offers_out",
            "handle_action_transactions",
        ]:
            return self._handle_credex_action(action)

        # Account management actions
        if action in [
            "handle_action_authorize_member",
            "handle_action_notifications",
            "handle_action_switch_account",
        ]:
            return self._handle_account_action(action)

        return self.auth_handler.handle_default_action()

    def _handle_auth_action(self, action: str) -> WhatsAppMessage:
        """Handle authentication and menu actions

        Args:
            action: Action to handle

        Returns:
            WhatsAppMessage: Response message
        """
        handler_map = {
            "handle_action_register": self.auth_handler.handle_action_register,
            "handle_action_menu": self.auth_handler.handle_action_menu,
        }
        return handler_map.get(action, self.auth_handler.handle_default_action)()

    def _handle_credex_action(self, action: str) -> WhatsAppMessage:
        """Handle credex-related actions

        Args:
            action: Action to handle

        Returns:
            WhatsAppMessage: Response message
        """
        handler_map = {
            "handle_action_offer_credex": self.credex_handler.handle_action_offer_credex,
            "handle_action_pending_offers_in": self.credex_handler.handle_default_action,
            "handle_action_pending_offers_out": self.credex_handler.handle_default_action,
            "handle_action_transactions": self.credex_handler.handle_default_action,
        }
        return handler_map.get(action, self.credex_handler.handle_default_action)()

    def _handle_account_action(self, action: str) -> WhatsAppMessage:
        """Handle account management actions

        Args:
            action: Action to handle

        Returns:
            WhatsAppMessage: Response message
        """
        handler_map = {
            "handle_action_authorize_member": self.account_handler.handle_action_authorize_member,
            "handle_action_notifications": self.account_handler.handle_action_notifications,
            "handle_action_switch_account": self.account_handler.handle_default_action,
        }
        return handler_map.get(action, self.account_handler.handle_default_action)()
