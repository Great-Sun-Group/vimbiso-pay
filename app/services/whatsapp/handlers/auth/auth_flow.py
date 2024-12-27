"""Authentication flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...base_handler import BaseActionHandler
from ...screens import REGISTER
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class AuthFlow(BaseActionHandler):
    """Handler for authentication flows with strict state management"""

    def __init__(self, state_manager: Any):
        """Initialize with state manager

        Args:
            state_manager: State manager instance
        """
        super().__init__(state_manager)
        self.credex_service = state_manager.get_credex_service()

    def handle_registration(self, register: bool = False) -> WhatsAppMessage:
        """Handle registration flow enforcing SINGLE SOURCE OF TRUTH

        Args:
            register: Whether to start registration

        Returns:
            WhatsAppMessage: Response message

        Raises:
            ValueError: If state validation fails or required data missing
        """
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id", "authenticated"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            validation = StateValidator.validate_before_access(
                current_state,
                required_fields
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Log registration attempt
            audit.log_flow_event(
                "auth_handler",
                "registration_start",
                None,
                {"channel_id": channel["identifier"]},
                "in_progress"
            )

            if register:
                return WhatsAppMessage.create_button(
                    to=channel["identifier"],
                    text=REGISTER,
                    buttons=[{
                        "id": "start_registration",
                        "title": "Become a Member"
                    }]
                )

            return self.handle_action_menu()

        except ValueError as e:
            # Get channel info for error response
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error response: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Registration error: {str(e)} for channel {channel_id}")
            return WhatsAppMessage.create_text(
                channel_id,
                "Error: Unable to process registration. Please try again."
            )

    def attempt_login(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Attempt login enforcing SINGLE SOURCE OF TRUTH

        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: Success flag and dashboard data

        Raises:
            ValueError: If state validation fails or required data missing
        """
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            validation = StateValidator.validate_before_access(
                current_state,
                required_fields
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Log login attempt
            audit.log_flow_event(
                "auth_handler",
                "login_attempt",
                None,
                {"channel_id": channel["identifier"]},
                "in_progress"
            )

            # Attempt login through service
            success, response = self.credex_service.services['auth'].login(
                channel["identifier"]
            )

            if not success:
                # Extract error details
                error_data = response.get("data", {}).get("action", {})
                error_type = error_data.get("type")
                error_code = error_data.get("details", {}).get("code")

                # Handle new user case
                if error_type == "ERROR_NOT_FOUND" and error_code == "NOT_FOUND":
                    audit.log_flow_event(
                        "auth_handler",
                        "login_new_user",
                        None,
                        {"channel_id": channel["identifier"]},
                        "success"
                    )
                    return False, None

                # Handle validation error
                if error_type == "ERROR_VALIDATION":
                    raise ValueError("Invalid login format")

                # Handle server error
                if error_type == "ERROR_INTERNAL":
                    raise ValueError("Service temporarily unavailable")

                # Handle other errors
                raise ValueError(response.get("message", "Authentication failed"))

            # Extract and validate required data
            member_id = response.get("data", {}).get("action", {}).get("details", {}).get("memberID")
            if not member_id:
                raise ValueError("Member ID not received")

            token = response.get("data", {}).get("action", {}).get("details", {}).get("token")
            if not token:
                raise ValueError("Authentication token not received")

            # Find personal account
            accounts = response.get("data", {}).get("dashboard", {}).get("accounts", [])
            personal_account = next(
                (account for account in accounts if account.get("accountType") == "PERSONAL"),
                None
            )
            if not personal_account:
                raise ValueError("Personal account not found")

            account_id = personal_account.get("accountID")
            if not account_id:
                raise ValueError("Account ID not found")

            # Prepare state update (SINGLE SOURCE OF TRUTH)
            new_state = {
                "member_id": member_id,
                "jwt_token": token,
                "authenticated": True,
                "account_id": account_id,
                "flow_data": {
                    "id": "user_state",
                    "step": 0
                }
            }

            # Validate state update
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid state update: {validation.error_message}")

            # Update state
            success, error = self.state_manager.update_state(new_state)
            if not success:
                raise ValueError(f"Failed to update state: {error}")

            # Log success
            audit.log_flow_event(
                "auth_handler",
                "login_success",
                None,
                {"channel_id": channel["identifier"]},
                "success"
            )

            return True, response.get("data", {})

        except ValueError as e:
            logger.error(f"Login error for channel {self.state_manager.get('channel', {}).get('identifier', 'unknown')}: {str(e)}")
            raise
