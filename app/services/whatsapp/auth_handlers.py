"""Authentication and menu handlers"""
import logging
from typing import Any

from .base_handler import BaseActionHandler
from .types import WhatsAppMessage
from .auth_validator import AuthFlowValidator
from .handlers.auth.auth_flow import AuthFlow
from .handlers.auth.menu_handler import MenuHandler

logger = logging.getLogger(__name__)


class AuthActionHandler(BaseActionHandler):
    """Handler for authentication and menu-related actions"""

    def __init__(self, state_manager: Any):
        """Initialize with state manager

        Args:
            state_manager: State manager instance
        """
        super().__init__(state_manager)
        self.validator = AuthFlowValidator()
        self.auth_flow = AuthFlow(state_manager)
        self.menu_handler = MenuHandler(state_manager)

    def handle_action_register(self, register: bool = False) -> WhatsAppMessage:
        """Handle registration flow

        Args:
            register: Whether to start registration

        Returns:
            WhatsAppMessage: Response message
        """
        try:
            # Validate state access at boundary
            validation = self.validator.validate_before_access(
                {"channel": self.state_manager.get("channel")},
                {"channel"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            return self.auth_flow.handle_registration(register)

        except ValueError as e:
            logger.error(f"Registration failed: {str(e)}")
            channel = self.state_manager.get("channel")
            return WhatsAppMessage.create_text(
                channel["identifier"] if channel else "unknown",
                f"Error: {str(e)}"
            )

    def handle_action_menu(self, message: str = None, login: bool = False) -> WhatsAppMessage:
        """Display main menu

        Args:
            message: Optional message to display
            login: Whether this is a login menu

        Returns:
            WhatsAppMessage: Menu message
        """
        try:
            # Validate state access at boundary
            validation = self.validator.validate_before_access(
                {"channel": self.state_manager.get("channel")},
                {"channel"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            return self.menu_handler.handle_menu(message, login)

        except ValueError as e:
            logger.error(f"Menu display failed: {str(e)}")
            channel = self.state_manager.get("channel")
            return WhatsAppMessage.create_text(
                channel["identifier"] if channel else "unknown",
                f"Error: {str(e)}"
            )

    def handle_hi(self) -> WhatsAppMessage:
        """Handle initial greeting

        Returns:
            WhatsAppMessage: Greeting message
        """
        try:
            # Validate state access at boundary
            validation = self.validator.validate_before_access(
                {"channel": self.state_manager.get("channel")},
                {"channel"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            return self.menu_handler.handle_hi()

        except ValueError as e:
            logger.error(f"Greeting failed: {str(e)}")
            channel = self.state_manager.get("channel")
            return WhatsAppMessage.create_text(
                channel["identifier"] if channel else "unknown",
                f"Error: {str(e)}"
            )

    def handle_refresh(self) -> WhatsAppMessage:
        """Handle dashboard refresh

        Returns:
            WhatsAppMessage: Refresh result message
        """
        try:
            # Validate state access at boundary
            validation = self.validator.validate_before_access(
                {
                    "channel": self.state_manager.get("channel"),
                    "member_id": self.state_manager.get("member_id"),
                    "jwt_token": self.state_manager.get("jwt_token")
                },
                {"channel", "member_id", "jwt_token"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            return self.menu_handler.handle_refresh()

        except ValueError as e:
            logger.error(f"Refresh failed: {str(e)}")
            channel = self.state_manager.get("channel")
            return WhatsAppMessage.create_text(
                channel["identifier"] if channel else "unknown",
                f"Error: {str(e)}"
            )
