"""
WhatsApp bot service implementation.
Handles message routing and bot interactions.
"""
import logging
from typing import Dict, Any, Optional, Tuple

from core.utils.exceptions import InvalidInputException
from core.utils.error_handler import error_decorator
from core.config.constants import CachedUser, get_greeting, GREETINGS
from services.credex.service import CredExService
from services.state.service import StateStage
from .types import BotServiceInterface, WhatsAppMessage
from .account_handlers import AccountActionHandler
from .auth_handlers import AuthActionHandler
from .handlers import CredexActionHandler

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

        # Initialize services
        self.credex_service = CredExService()
        self.action_handler = WhatsAppActionHandler(self)

        # Initialize state if needed
        self._initialize_state()
        logger.debug(f"Current state: {self.current_state}")

        self.response = self.handle()
        logger.debug(f"Final response: {self.response}")

    def _initialize_state(self) -> None:
        """Initialize state if empty with proper error handling"""
        try:
            self.current_state = self.state.get_state(self.user.mobile_number)
        except Exception as e:
            logger.info(f"No existing state found: {str(e)}")
            # Initialize fresh state with required fields
            initial_state = {
                "stage": StateStage.INIT.value,
                "option": "handle_action_menu",
                "last_updated": None,
                "profile": None,
                "current_account": None
            }
            self.state.update_state(
                user_id=self.user.mobile_number,
                new_state=initial_state,
                stage=StateStage.INIT.value,
                update_from="init",
                option="handle_action_menu"
            )
            self.current_state = self.state.get_state(self.user.mobile_number)

    def refresh(self, reset: bool = True, silent: bool = True) -> Optional[str]:
        """Refresh user profile and state information.

        Args:
            reset: Whether to reset state
            silent: Whether to suppress notifications

        Returns:
            Optional[str]: Error message if any
        """
        try:
            # First refresh member info
            result = self.credex_service.refresh_member_info(
                phone=self.user.mobile_number,
                reset=reset,
                silent=silent
            )

            # Then refresh state if needed
            if reset:
                initial_state = {
                    "stage": StateStage.INIT.value,
                    "option": "handle_action_menu",
                    "last_updated": None,
                    "profile": None,
                    "current_account": None
                }
                self.state.reset_state(self.user.mobile_number, preserve_auth=True)
                self.state.update_state(
                    user_id=self.user.mobile_number,
                    new_state=initial_state,
                    stage=StateStage.INIT.value,
                    update_from="refresh",
                    option="handle_action_menu"
                )
                self.current_state = self.state.get_state(self.user.mobile_number)

            return result
        except Exception as e:
            logger.error(f"Error refreshing state: {str(e)}")
            return str(e)

    def _handle_greeting(self) -> Dict[str, Any]:
        """Handle greeting messages with proper state management.

        Returns:
            Dict[str, Any]: Response message
        """
        logger.info("Handling greeting message")

        try:
            # Reset state to ensure fresh start
            self.state.reset_state(self.user.mobile_number, preserve_auth=True)

            # First try to login
            success, login_msg = self._attempt_login()
            if not success:
                return self._handle_login_failure(login_msg)

            # Get fresh dashboard data
            success, data = self._get_dashboard_data()
            if not success:
                return self.get_response_template(data.get("message", "Failed to load profile"))

            # Initialize state with dashboard data
            initial_state = {
                "stage": StateStage.MENU.value,
                "option": "handle_action_menu",
                "profile": data,
                "current_account": None,
                "last_updated": None
            }
            self.state.update_state(
                user_id=self.user.mobile_number,
                new_state=initial_state,
                stage=StateStage.MENU.value,
                update_from="greeting",
                option="handle_action_menu"
            )
            self.current_state = self.state.get_state(self.user.mobile_number)

            # Format greeting
            greeting = f"*{get_greeting(self.user.first_name)}*\n\n"

            # Get menu and combine with greeting
            return self.action_handler.auth_handler.handle_action_menu(message=greeting)

        except Exception as e:
            logger.error(f"Error handling greeting: {str(e)}")
            return self.get_response_template("Sorry, something went wrong. Please try again.")

    def _attempt_login(self) -> Tuple[bool, str]:
        """Attempt to login user with proper error handling"""
        try:
            return self.credex_service._auth.login(self.user.mobile_number)
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False, str(e)

    def _handle_login_failure(self, login_msg: str) -> Dict[str, Any]:
        """Handle login failure scenarios"""
        if any(phrase in login_msg.lower() for phrase in ["new user", "new here"]):
            return self.action_handler.auth_handler.handle_action_register(register=True)
        return self.get_response_template(login_msg)

    def _get_dashboard_data(self) -> Tuple[bool, Dict[str, Any]]:
        """Get dashboard data with proper error handling"""
        try:
            return self.credex_service._member.get_dashboard(self.user.mobile_number)
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")
            return False, {"message": str(e)}

    @error_decorator
    def handle(self) -> Dict[str, Any]:
        """Process the incoming message and generate response.

        Returns:
            Dict[str, Any]: Response message
        """
        try:
            # Handle greeting messages
            if self.message_type == "text" and self.body.lower() in GREETINGS:
                return self._handle_greeting()

            # Get current stage and option from state
            current_stage = self.state.get_stage(self.user.mobile_number)
            current_option = self.current_state.get("option")

            # Handle form submissions
            if self.message_type == "nfm_reply":
                # Check for registration form submission
                if current_stage == StateStage.AUTH.value and current_option == "registration":
                    return self.action_handler.auth_handler.handle_action_register()
                # Check for credex form submission
                elif (current_stage == StateStage.CREDEX.value or
                        current_option == "handle_action_offer_credex"):
                    return self.action_handler.credex_handler.handle_action_offer_credex()
                else:
                    logger.error(f"Invalid stage/option for form submission: {current_stage}/{current_option}")
                    return self.get_response_template("Invalid form submission. Please try again.")

            # For other messages, check if body is an action command
            action = (
                self.body if isinstance(self.body, str) and self.body.startswith("handle_action_")
                else current_stage
            )

            logger.info(f"Entry point: {action}")
            return self.action_handler.handle_action(action)

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            return self.get_response_template("Sorry, something went wrong. Please try again.")


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
        """Route action to appropriate handler with proper state validation

        Args:
            action: Action to handle

        Returns:
            WhatsAppMessage: Response message
        """
        try:
            # Authentication and menu actions
            if action in ["handle_action_register", "handle_action_menu"]:
                return self._handle_auth_action(action)

            # Credex-related actions
            if action in [
                "handle_action_offer_credex",
                "handle_action_pending_offers_in",
                "handle_action_pending_offers_out",
                "handle_action_transactions",
                StateStage.CREDEX.value,
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

        except Exception as e:
            logger.error(f"Error handling action {action}: {str(e)}")
            return self.auth_handler.handle_default_action()

    def _handle_auth_action(self, action: str, login: bool = False) -> WhatsAppMessage:
        """Handle authentication and menu actions with proper state transitions

        Args:
            action: Action to handle
            login: Whether to force login refresh

        Returns:
            WhatsAppMessage: Response message
        """
        try:
            if action == "handle_action_menu":
                return self.auth_handler.handle_action_menu(login=login)
            elif action == "handle_action_register":
                return self.auth_handler.handle_action_register()
            return self.auth_handler.handle_default_action()
        except Exception as e:
            logger.error(f"Error handling auth action {action}: {str(e)}")
            return self.auth_handler.handle_default_action()

    def _handle_credex_action(self, action: str) -> WhatsAppMessage:
        """Handle credex-related actions with proper state validation

        Args:
            action: Action to handle

        Returns:
            WhatsAppMessage: Response message
        """
        try:
            handler_map = {
                "handle_action_offer_credex": self.credex_handler.handle_action_offer_credex,
                "handle_action_pending_offers_in": self.credex_handler.handle_default_action,
                "handle_action_pending_offers_out": self.credex_handler.handle_default_action,
                "handle_action_transactions": self.credex_handler.handle_default_action,
                StateStage.CREDEX.value: self.credex_handler.handle_action_offer_credex,
            }
            return handler_map.get(action, self.credex_handler.handle_default_action)()
        except Exception as e:
            logger.error(f"Error handling credex action {action}: {str(e)}")
            return self.credex_handler.handle_default_action()

    def _handle_account_action(self, action: str) -> WhatsAppMessage:
        """Handle account management actions with proper state validation

        Args:
            action: Action to handle

        Returns:
            WhatsAppMessage: Response message
        """
        try:
            handler_map = {
                "handle_action_authorize_member": self.account_handler.handle_action_authorize_member,
                "handle_action_notifications": self.account_handler.handle_action_notifications,
                "handle_action_switch_account": self.account_handler.handle_action_switch_account,
            }
            return handler_map.get(action, self.account_handler.handle_default_action)()
        except Exception as e:
            logger.error(f"Error handling account action {action}: {str(e)}")
            return self.account_handler.handle_default_action()
