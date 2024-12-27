"""Authentication flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from ...screens import REGISTER
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def handle_registration(state_manager: Any, register: bool = False) -> WhatsAppMessage:
    """Handle registration flow enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        register: Whether to start registration

    Returns:
        WhatsAppMessage: Response message
    """
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info
        channel = state_manager.get("channel")

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

        return handle_action_menu(state_manager)

    except ValueError as e:
        # Get channel info for error response
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error response: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Registration error: {str(e)} for channel {channel_id}")
        return WhatsAppMessage.create_text(
            channel_id,
            "Error: Unable to process registration. Please try again."
        )


def attempt_login(state_manager: Any, credex_service: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Attempt login enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        credex_service: CredEx service instance

    Returns:
        Tuple[bool, Optional[Dict[str, Any]]]: Success flag and dashboard data
    """
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info
        channel = state_manager.get("channel")

        # Log login attempt
        audit.log_flow_event(
            "auth_handler",
            "login_attempt",
            None,
            {"channel_id": channel["identifier"]},
            "in_progress"
        )

        # Attempt login through service
        success, response = credex_service.services['auth'].login(
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
                "flow_type": "auth",
                "step": 0
            }
        }

        # Update state
        state_manager.update(new_state)

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
        # Get channel info for error logging
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
            logger.error(f"Login error for channel {channel_id}: {str(e)}")
        except ValueError:
            logger.error(f"Login error for unknown channel: {str(e)}")
        raise


def handle_action_menu(state_manager: Any) -> WhatsAppMessage:
    """Handle menu action with proper state validation

    Args:
        state_manager: State manager instance

    Returns:
        WhatsAppMessage: Menu response
    """
    # Implementation would go here
    pass
