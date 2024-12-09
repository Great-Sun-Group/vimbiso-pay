from .account_handlers import AccountActionHandler
from .auth_handlers import AuthActionHandler
from .credex_handlers import CredexActionHandler
from .types import WhatsAppMessage, CredexBotService


class WhatsAppActionHandler:
    """Main handler for WhatsApp actions"""

    def __init__(self, service: "CredexBotService"):
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
