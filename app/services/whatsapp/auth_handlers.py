"""Authentication and menu handlers"""
import logging

from .base_handler import BaseActionHandler
from .types import WhatsAppMessage
from .auth_validator import AuthFlowValidator
from .handlers.auth.auth_flow import AuthFlow
from .handlers.auth.menu_handler import MenuHandler

logger = logging.getLogger(__name__)


class AuthActionHandler(BaseActionHandler):
    """Handler for authentication and menu-related actions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = AuthFlowValidator()
        self.auth_flow = AuthFlow(self.service)
        self.menu_handler = MenuHandler(self.service)

    def handle_action_register(self, register: bool = False) -> WhatsAppMessage:
        """Handle registration flow"""
        return self.auth_flow.handle_registration(register)

    def handle_action_menu(self, message: str = None, login: bool = False) -> WhatsAppMessage:
        """Display main menu"""
        return self.menu_handler.handle_menu(message, login)

    def handle_hi(self) -> WhatsAppMessage:
        """Handle initial greeting"""
        return self.menu_handler.handle_hi()

    def handle_refresh(self) -> WhatsAppMessage:
        """Handle dashboard refresh"""
        return self.menu_handler.handle_refresh()
