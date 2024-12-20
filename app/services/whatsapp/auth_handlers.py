"""Authentication and menu handlers"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.state_validator import StateValidator
from core.utils.flow_audit import FlowAuditLogger
from .base_handler import BaseActionHandler
from .handlers.member.dashboard import DashboardFlow
from .screens import REGISTER
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class AuthActionHandler(BaseActionHandler):
    """Handler for authentication and menu-related actions"""

    def handle_action_register(self, register: bool = False) -> WhatsAppMessage:
        """Handle registration flow"""
        try:
            # Log registration attempt
            audit.log_flow_event(
                "auth_handler",
                "registration_start",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "in_progress"
            )

            if register:
                return WhatsAppMessage.create_button(
                    to=self.service.user.mobile_number,
                    text=REGISTER,
                    buttons=[{
                        "id": "start_registration",
                        "title": "Introduce yourself"
                    }]
                )

            return self.handle_action_menu()

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            audit.log_flow_event(
                "auth_handler",
                "registration_error",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "failure",
                str(e)
            )
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Registration failed. Please try again."
            )

    def _attempt_login(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Attempt login and store JWT token"""
        try:
            # Log login attempt
            audit.log_flow_event(
                "auth_handler",
                "login_attempt",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "in_progress"
            )

            # Attempt login
            success, response = self.service.credex_service._auth.login(
                self.service.user.mobile_number
            )

            if not success:
                if any(
                    phrase in response.lower()
                    for phrase in ["new user", "new here", "member not found"]
                ):
                    audit.log_flow_event(
                        "auth_handler",
                        "login_new_user",
                        None,
                        {"mobile_number": self.service.user.mobile_number},
                        "success"
                    )
                    return False, None

                logger.error(f"Login failed: {response}")
                audit.log_flow_event(
                    "auth_handler",
                    "login_error",
                    None,
                    {"mobile_number": self.service.user.mobile_number},
                    "failure",
                    str(response)
                )
                return False, None

            # Extract JWT token and dashboard data
            jwt_token = self.service.credex_service._auth._jwt_token
            if not jwt_token:
                audit.log_flow_event(
                    "auth_handler",
                    "login_error",
                    None,
                    {"mobile_number": self.service.user.mobile_number},
                    "failure",
                    "No JWT token received"
                )
                return False, None

            dashboard_data = response.get("data", {})
            logger.info(f"Dashboard data from login: {dashboard_data}")

            # Extract member ID
            member_id = dashboard_data.get("action", {}).get("details", {}).get("memberID")

            # Find account with accountType=PERSONAL
            accounts = dashboard_data.get("dashboard", {}).get("accounts", [])
            personal_account = None
            for account in accounts:
                if account.get("accountType") == "PERSONAL":
                    personal_account = account
                    break

            if not personal_account:
                logger.error("Personal account not found")
                audit.log_flow_event(
                    "auth_handler",
                    "login_error",
                    None,
                    {"mobile_number": self.service.user.mobile_number},
                    "failure",
                    "Personal account not found"
                )
                return False, None

            account_id = personal_account.get("accountID")

            # Get current state for transition logging
            current_state = self.service.user.state.state or {}

            # First set the JWT token to ensure proper propagation
            self.service.user.state.set_jwt_token(jwt_token)

            # Prepare new state
            new_state = {
                "authenticated": True,
                "profile": dashboard_data,
                "flow_data": None,  # Clear any existing flow data
                "member_id": member_id,
                "account_id": account_id,
                "current_account": personal_account,  # Store full account data
                "jwt_token": jwt_token  # Include token in validation
            }

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "auth_handler",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return False, None

            # Log state transition
            audit.log_state_transition(
                "auth_handler",
                current_state,
                new_state,
                "success"
            )

            # Update state
            self.service.user.state.update_state(new_state, "login_success")

            # Ensure token is propagated to credex service
            self.service.credex_service = self.service.user.state.get_or_create_credex_service()

            audit.log_flow_event(
                "auth_handler",
                "login_success",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "success"
            )

            return True, dashboard_data

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            audit.log_flow_event(
                "auth_handler",
                "login_error",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "failure",
                str(e)
            )
            return False, None

    def _show_dashboard(self, flow_type: str = "view", message: Optional[str] = None) -> WhatsAppMessage:
        """Display dashboard without flow processing"""
        try:
            # Get current state for transition logging
            current_state = self.service.user.state.state or {}

            # Validate current state
            validation = StateValidator.validate_state(current_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "auth_handler",
                    "state_validation_error",
                    None,
                    current_state,
                    "failure",
                    validation.error_message
                )
                # Attempt recovery from last valid state
                last_valid = audit.get_last_valid_state("auth_handler")
                if last_valid:
                    current_state = last_valid

            # Prepare new state
            new_state = {
                "flow_data": None,
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token"),
                "authenticated": current_state.get("authenticated", False)
            }

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "auth_handler",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    f"Failed to update state: {validation.error_message}"
                )

            # Log state transition
            audit.log_state_transition(
                "auth_handler",
                current_state,
                new_state,
                "success"
            )

            # Update state
            self.service.user.state.update_state(new_state, "clear_flow")

            # Initialize dashboard flow
            flow = DashboardFlow(
                flow_type=flow_type,
                success_message=message
            )

            # Use cached credex service
            flow.credex_service = self.service.credex_service
            flow.data = {
                "mobile_number": self.service.user.mobile_number
            }

            # Complete flow directly
            return flow.complete()

        except Exception as e:
            logger.error(f"Dashboard display error: {str(e)}")
            audit.log_flow_event(
                "auth_handler",
                "dashboard_error",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "failure",
                str(e)
            )
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Failed to load dashboard. Please try again."
            )

    def handle_action_menu(self, message: Optional[str] = None, login: bool = False) -> WhatsAppMessage:
        """Display main menu"""
        try:
            # Handle login if needed
            if login:
                success, dashboard_data = self._attempt_login()
                if not success:
                    return self.handle_action_register(register=True)

            # Show dashboard directly
            return self._show_dashboard(
                flow_type="login" if login else "view",
                message=message
            )

        except Exception as e:
            logger.error(f"Menu error: {str(e)}")
            audit.log_flow_event(
                "auth_handler",
                "menu_error",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "failure",
                str(e)
            )
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Failed to load menu. Please try again."
            )

    def handle_hi(self) -> WhatsAppMessage:
        """Handle initial greeting"""
        audit.log_flow_event(
            "auth_handler",
            "greeting",
            None,
            {"mobile_number": self.service.user.mobile_number},
            "in_progress"
        )
        return self.handle_action_menu(login=True)

    def handle_refresh(self) -> WhatsAppMessage:
        """Handle dashboard refresh"""
        audit.log_flow_event(
            "auth_handler",
            "refresh",
            None,
            {"mobile_number": self.service.user.mobile_number},
            "in_progress"
        )
        return self.handle_action_menu(message="Dashboard refreshed")
