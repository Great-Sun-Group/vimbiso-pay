"""Authentication flow implementation"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.flow_audit import FlowAuditLogger

from ...base_handler import BaseActionHandler
from ...screens import REGISTER
from ...state_manager import StateManager
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class AuthFlow(BaseActionHandler):
    """Handler for authentication flows"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle_registration(self, register: bool = False) -> WhatsAppMessage:
        """Handle registration flow"""
        try:
            # Get channel identifier from user
            channel_id = self.service.user.channel_identifier

            # Log registration attempt with channel info
            audit_context = {
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                }
            }

            audit.log_flow_event(
                "auth_handler",
                "registration_start",
                None,
                audit_context,
                "in_progress"
            )

            if register:
                return WhatsAppMessage.create_button(
                    to=channel_id,
                    text=REGISTER,
                    buttons=[{
                        "id": "start_registration",
                        "title": "Become a Member"
                    }]
                )

            return self.service.auth_handler.handle_action_menu()

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")

            # Get channel identifier from user
            channel_id = self.service.user.channel_identifier

            audit.log_flow_event(
                "auth_handler",
                "registration_error",
                None,
                {
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id
                    },
                    "error": str(e)
                },
                "failure"
            )

            return WhatsAppMessage.create_text(
                channel_id,
                "Registration failed. Please try again."
            )

    def attempt_login(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Attempt login and store JWT token"""
        try:
            # Get channel identifier from user
            channel_id = self.service.user.channel_identifier

            # Log login attempt with channel info
            audit_context = {
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                }
            }
            audit.log_flow_event(
                "auth_handler",
                "login_attempt",
                None,
                audit_context,
                "in_progress"
            )

            # Attempt login using channel identifier
            success, response = self.service.credex_service._auth.login(
                channel_id  # Use channel identifier from state
            )

            if not success:
                # Extract error details from response
                error_data = response.get("data", {}).get("action", {})
                error_type = error_data.get("type")
                error_details = error_data.get("details", {})
                error_code = error_details.get("code")
                error_reason = error_details.get("reason", "")
                error_msg = response.get("message", "")

                # Handle different error types based on API spec
                # Handle different error types based on API spec
                if error_type == "ERROR_NOT_FOUND" and error_code == "NOT_FOUND":
                    # This is a new user case
                    audit.log_flow_event(
                        "auth_handler",
                        "login_new_user",
                        None,
                        audit_context,
                        "success"
                    )
                    return False, None

                if error_type == "ERROR_VALIDATION":
                    # Handle validation errors
                    logger.error(f"Validation error: {error_reason}")
                    audit.log_flow_event(
                        "auth_handler",
                        "validation_error",
                        None,
                        {**audit_context, "error": error_reason},
                        "failure"
                    )
                    return False, {"message": "Invalid format. Please try again."}

                if error_type == "ERROR_INTERNAL":
                    # Handle server errors
                    logger.error(f"Server error: {error_reason}")
                    audit.log_flow_event(
                        "auth_handler",
                        "server_error",
                        None,
                        {**audit_context, "error": error_reason},
                        "failure"
                    )
                    return False, {
                        "message": "😔 We're having some technical difficulties. "
                        "Please try again in a few minutes. Thank you for your patience!"
                    }

                # Handle other login failures
                logger.error(f"Login failed: {error_msg}")
                audit.log_flow_event(
                    "auth_handler",
                    "login_error",
                    None,
                    {
                        **audit_context,
                        "error": error_msg
                    },
                    "failure"
                )
                return False, None

            # Extract JWT token and dashboard data
            jwt_token = self.service.credex_service._auth._jwt_token
            if not jwt_token:
                audit.log_flow_event(
                    "auth_handler",
                    "login_error",
                    None,
                    {
                        **audit_context,
                        "error": "No JWT token received"
                    },
                    "failure"
                )
                return False, None

            dashboard_data = response.get("data", {})
            logger.info(f"Dashboard data from login: {dashboard_data}")

            # Extract member ID
            member_id = (
                response.get("data", {})
                .get("action", {})
                .get("details", {})
                .get("memberID")
            )

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
                    {
                        **audit_context,
                        "error": "Personal account not found"
                    },
                    "failure"
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
                    "actor": dashboard_data.get("action", {}).get("actor", member_id),  # Use member_id as actor
                    "details": dashboard_data.get("action", {}).get("details", {})
                },
                "dashboard": {
                    "member": dashboard_data.get("dashboard", {}).get("member", {}),
                    "accounts": dashboard_data.get("dashboard", {}).get("accounts", [])
                }
            }

            # Prepare new state with member-centric structure
            new_state = {
                # Core identity at top level - SINGLE SOURCE OF TRUTH
                "member_id": member_id,  # Primary identifier

                # Channel info at top level - SINGLE SOURCE OF TRUTH
                "channel": StateManager.create_channel_data(
                    identifier=channel_id,
                    channel_type="whatsapp"
                ),

                # Authentication and account
                "authenticated": True,
                "account_id": account_id,
                "current_account": personal_account,
                "jwt_token": jwt_token,

                # Profile and flow data
                "profile": profile_data,
                "flow_data": {  # Initialize empty flow data structure
                    "id": "user_state",
                    "step": 0,
                    "data": {
                        "account_id": account_id,
                        "flow_type": "auth",
                        "_validation_context": {},
                        "_validation_state": {}
                    },
                    "_previous_data": {}
                },

                # Validation context
                "_validation_context": {},
                "_validation_state": {},
                "_last_updated": audit.get_current_timestamp()
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

            # Update audit context with member info after successful login
            audit_context["member_id"] = member_id
            audit.log_flow_event(
                "auth_handler",
                "login_success",
                None,
                audit_context,
                "success"
            )

            return True, dashboard_data

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            audit.log_flow_event(
                "auth_handler",
                "login_error",
                None,
                {
                    **audit_context,
                    "error": str(e)
                },
                "failure"
            )
            return False, None
