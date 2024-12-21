"""Authentication flow implementation"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.flow_audit import FlowAuditLogger
from ...base_handler import BaseActionHandler
from ...types import WhatsAppMessage
from ...screens import REGISTER

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class AuthFlow(BaseActionHandler):
    """Handler for authentication flows"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle_registration(self, register: bool = False) -> WhatsAppMessage:
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
                        "title": "Provide your name to continue"
                    }]
                )

            return self.service.auth_handler.handle_action_menu()

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

    def attempt_login(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
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

            # Structure profile data properly
            profile_data = {
                "action": {
                    "id": dashboard_data.get("action", {}).get("id", ""),
                    "type": dashboard_data.get("action", {}).get("type", "login"),
                    "timestamp": dashboard_data.get("action", {}).get("timestamp", ""),
                    "actor": dashboard_data.get("action", {}).get("actor", self.service.user.mobile_number),
                    "details": dashboard_data.get("action", {}).get("details", {})
                },
                "dashboard": {
                    "member": dashboard_data.get("dashboard", {}).get("member", {}),
                    "accounts": dashboard_data.get("dashboard", {}).get("accounts", [])
                }
            }

            # Prepare new state with validation context
            new_state = {
                "authenticated": True,
                "profile": profile_data,
                "flow_data": None,  # No flow data needed for initial state
                "member_id": member_id,
                "account_id": account_id,
                "current_account": personal_account,
                "jwt_token": jwt_token,
                "mobile_number": self.service.user.mobile_number,
                "_validation_context": {},
                "_validation_state": {}
            }

            # Validate login state specifically
            validation = self.service.auth_handler.validator.validate_login_state(new_state)
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
