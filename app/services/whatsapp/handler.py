"""
WhatsApp bot service implementation.
Handles message routing and bot interactions.
"""
import json
import logging
from typing import Any, Dict, Optional, Tuple

from core.config.constants import GREETINGS, CachedUser, get_greeting
from core.utils.error_handler import error_decorator
from core.utils.exceptions import InvalidInputException
from services.credex.service import CredExService
from services.state.service import StateStage

from .account_handlers import AccountActionHandler
from .auth_handlers import AuthActionHandler
from .handlers import CredexActionHandler
from .handlers.member import MemberRegistrationHandler
from .types import BotServiceInterface, WhatsAppMessage

logger = logging.getLogger(__name__)


class CredexBotService(BotServiceInterface):
    """Service for handling WhatsApp bot interactions"""

    def __init__(self, payload: Dict[str, Any], user: CachedUser) -> None:
        """Initialize the bot service.

        Args:
            payload: Message payload from WhatsApp
            user: CachedUser instance
        """
        logger.debug(f"Initializing CredexBotService with payload: {json.dumps(payload, indent=2)}")
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
        logger.debug(f"Current state: {json.dumps(self.current_state, indent=2)}")

        self.response = self.handle()
        logger.debug(f"Final response: {json.dumps(self.response, indent=2)}")

    def _initialize_state(self) -> None:
        """Initialize state if empty with proper error handling"""
        try:
            self.current_state = self.state.get_state(self.user.mobile_number)
            logger.debug(f"Retrieved state: {json.dumps(self.current_state, indent=2)}")

            # Restore JWT token if present in state
            if self.current_state.get("jwt_token"):
                self.credex_service.jwt_token = self.current_state["jwt_token"]
                logger.debug("Restored JWT token from state")

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
            logger.debug(f"Initialized new state: {json.dumps(self.current_state, indent=2)}")

    def refresh(self, reset: bool = True, silent: bool = True) -> Optional[str]:
        """Refresh user profile and state information.

        Args:
            reset: Whether to reset state
            silent: Whether to suppress notifications

        Returns:
            Optional[str]: Error message if any
        """
        try:
            # Save current stage and option before refresh
            current_stage = self.state.get_stage(self.user.mobile_number)
            current_option = self.current_state.get("option")

            # First refresh member info
            result = self.credex_service.refresh_member_info(
                phone=self.user.mobile_number,
                reset=reset,
                silent=silent
            )

            # Then refresh state if needed, preserving stage and option
            if reset:
                initial_state = {
                    "stage": current_stage,  # Preserve current stage
                    "option": current_option,  # Preserve current option
                    "last_updated": None,
                    "profile": None,
                    "current_account": None
                }
                self.state.reset_state(self.user.mobile_number, preserve_auth=True)
                self.state.update_state(
                    user_id=self.user.mobile_number,
                    new_state=initial_state,
                    stage=current_stage,  # Keep current stage
                    update_from="refresh",
                    option=current_option  # Keep current option
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
            logger.debug(f"Login attempt result: success={success}, msg={login_msg}")
            if not success:
                return self._handle_login_failure(login_msg)

            # Store JWT token in state
            if self.credex_service.jwt_token:
                self.current_state["jwt_token"] = self.credex_service.jwt_token
                logger.debug("Stored JWT token in state")

            # Get fresh dashboard data
            success, data = self._get_dashboard_data()
            logger.debug(f"Dashboard data result: success={success}")
            if not success:
                return self.get_response_template(data.get("message", "Failed to load profile"))

            # Initialize state with dashboard data
            initial_state = {
                "stage": StateStage.MENU.value,
                "option": "handle_action_menu",
                "profile": data,
                "current_account": None,
                "last_updated": None,
                "jwt_token": self.credex_service.jwt_token  # Include token in state
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
            success, msg = self.credex_service._auth.login(self.user.mobile_number)
            if success:
                # Propagate token to bot service
                self.credex_service.jwt_token = self.credex_service._auth.jwt_token
                logger.debug("JWT token propagated after successful login")
            return success, msg
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
        """Process the incoming message and generate response."""
        try:
            # Get current stage and option from state
            current_stage = self.state.get_stage(self.user.mobile_number)
            current_option = self.current_state.get("option")
            logger.debug(f"Current stage: {current_stage}")
            logger.debug(f"Current option: {current_option}")

            # Handle greeting messages
            if self.message_type == "text":
                logger.debug(f"Checking if '{self.body}' is a greeting")
                if self.body and self.body.lower() in GREETINGS:
                    logger.info(f"Recognized greeting: {self.body}")
                    return self._handle_greeting()
                logger.debug("Not a greeting message")

                # Handle text input during registration
                if current_stage == StateStage.REGISTRATION.value:
                    return self.action_handler.registration_handler.handle_registration()

            # Handle cancel_offer commands first
            if (self.message_type == "text" and
                isinstance(self.body, str) and
                    self.body.startswith("cancel_offer_")):
                logger.debug("Handling cancel_offer command")
                return self.action_handler.credex_handler.handle_action_offer_credex()

            # Handle interactive messages (including list selections and button replies)
            if self.message_type == "interactive":
                interactive = self.message.get("interactive", {})
                interactive_type = interactive.get("type")
                logger.debug(f"Interactive type: {interactive_type}")

                # Handle button replies
                if interactive_type == "button_reply":
                    button_id = interactive.get("button_reply", {}).get("id")
                    logger.debug(f"Button ID: {button_id}")

                    # Handle specific button responses
                    if button_id == "confirm_tier_upgrade":
                        logger.debug("Handling tier upgrade confirmation")
                        return self.action_handler.handle_action("handle_action_confirm_tier_upgrade")

                # For multi-step flows, prioritize current_option over stage
                if current_option and current_option.startswith("handle_action_"):
                    logger.debug(f"Using current option for multi-step flow: {current_option}")
                    return self.action_handler.handle_action(current_option)

                # Use current stage/option to route to correct handler
                if current_stage == StateStage.CREDEX.value or current_option == "handle_action_offer_credex":
                    return self.action_handler.credex_handler.handle_action_offer_credex()
                elif current_stage == StateStage.AUTH.value:
                    return self.action_handler.auth_handler.handle_action_menu()
                elif current_stage == StateStage.REGISTRATION.value:
                    return self.action_handler.registration_handler.handle_registration()
                else:
                    # Default to current stage
                    return self.action_handler.handle_action(current_stage)

            # For other messages, determine action based on body, option, or stage
            action = None
            if isinstance(self.body, str) and self.body.startswith("handle_action_"):
                action = self.body
            elif current_option and current_option.startswith("handle_action_"):
                # Prioritize current_option for multi-step flows
                action = current_option
            else:
                action = current_stage

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
        self.registration_handler = MemberRegistrationHandler(service)

    def handle_action(self, action: str) -> WhatsAppMessage:
        """Route action to appropriate handler with proper state validation

        Args:
            action: Action to handle

        Returns:
            WhatsAppMessage: Response message
        """
        try:
            # Authentication and menu actions
            if action in [
                "handle_action_register",
                "handle_action_menu",
                "handle_action_upgrade_tier",
                "handle_action_confirm_tier_upgrade"
            ]:
                return self._handle_auth_action(action)

            # Registration actions
            if action == StateStage.REGISTRATION.value:
                return self.registration_handler.handle_registration()

            # Credex-related actions
            if action in [
                "handle_action_offer_credex",
                "handle_action_pending_offers_in",
                "handle_action_pending_offers_out",
                "handle_action_accept_offers",
                "handle_action_decline_offers",
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
            handler_map = {
                "handle_action_menu": lambda: self.auth_handler.handle_action_menu(login=login),
                "handle_action_register": self.auth_handler.handle_action_register,
                "handle_action_upgrade_tier": self.auth_handler.handle_action_upgrade_tier,
                "handle_action_confirm_tier_upgrade": self.auth_handler.handle_action_confirm_tier_upgrade
            }
            return handler_map.get(action, self.auth_handler.handle_default_action)()
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
                "handle_action_pending_offers_in": self.credex_handler.handle_action_accept_offers,  # Route to accept flow
                "handle_action_pending_offers_out": self.credex_handler.handle_action_pending_offers_out,
                "handle_action_accept_offers": self.credex_handler.handle_action_accept_offers,
                "handle_action_decline_offers": self.credex_handler.handle_action_decline_offers,
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
