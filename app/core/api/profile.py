"""Profile and state management through validation"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)


def _get_action_message(action: Dict[str, Any], action_type: str) -> str:
    """Get action message from response"""
    # Return explicit message if present
    if action.get("message"):
        return action["message"]

    # Check details for message
    if action.get("details", {}).get("message"):
        return action["details"]["message"]

    return ""


def _structure_profile_data(
    api_response: dict,
    state_manager: Any,
    action_type: str = "update"
) -> Dict[str, Any]:
    """Structure API response through state validation"""
    try:
        data = api_response.get("data", {})
        dashboard = data.get("dashboard", {})
        action = data.get("action", {})

        # Get channel through state validation
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Invalid channel state")

        return {
            "action": {
                "id": action.get("id", ""),
                "type": action.get("type", action_type),
                "timestamp": datetime.now().isoformat(),
                "actor": channel["identifier"],
                "details": action.get("details", {}),
                "message": _get_action_message(action, action_type),
                "status": action.get("status", "")
            },
            "dashboard": dashboard
        }

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "structure_profile",
                "action_type": action_type
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        return {}


def _handle_account_setup(
    dashboard_data: Dict[str, Any],
    state_manager: Any
) -> bool:
    """Handle account setup through state validation"""
    try:
        # Extract and validate accounts
        accounts = dashboard_data.get("accounts", [])
        if not isinstance(accounts, list) or not accounts:
            raise StateException("No valid accounts found")

        # Process accounts while maintaining structure
        processed_accounts = []
        required_fields = {"accountType", "accountHandle", "accountID"}

        for account in accounts:
            # Handle nested account structure
            account_data = (
                account.get("data") if account.get("success")
                else account
            )

            # Validate account structure
            if not isinstance(account_data, dict):
                continue

            if not all(
                isinstance(account_data.get(field), str)
                for field in required_fields
            ):
                continue

            processed_accounts.append(account_data)

        if not processed_accounts:
            raise StateException("No valid accounts after processing")

        # Find personal account through validation
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Invalid channel state")

        # Prioritize personal account, fallback to channel match
        personal_account = next(
            (acc for acc in processed_accounts if acc["accountType"] == "PERSONAL"),
            next(
                (acc for acc in processed_accounts if acc["accountHandle"] == channel["identifier"]),
                None
            )
        )

        if not personal_account:
            raise StateException("No valid personal account found")

        # Update state through validation
        state_update = {
            "accounts": processed_accounts,  # Store all accounts at top level
            "active_account_id": personal_account["accountID"]  # Reference by ID
        }

        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to update account state: {error}")

        logger.info(f"Successfully set up account: {personal_account['accountHandle']}")
        return True

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={"operation": "account_setup"}
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        return False


def update_profile_from_response(
    api_response: Dict[str, Any],
    state_manager: Any,
    action_type: str,
    update_from: str,
    token: Optional[str] = None
) -> bool:
    """Update profile through state validation"""
    try:
        # Validate response format
        if not isinstance(api_response, dict):
            raise StateException("Invalid API response format")

        # Structure profile data through validation
        profile_data = _structure_profile_data(
            api_response,
            state_manager,
            action_type
        )
        if not profile_data:
            raise StateException("Failed to structure profile data")

        # Prepare state update
        state_update = {"flow_data": {"data": profile_data}}

        # Add token if provided
        if token:
            state_update["jwt_token"] = token

        # Update state through validation
        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to update state: {error}")

        # Handle account setup if needed
        dashboard_data = api_response.get("data", {}).get("dashboard")
        if dashboard_data:
            if not _handle_account_setup(dashboard_data, state_manager):
                raise StateException("Failed to set up accounts")

        logger.info(f"State updated from {update_from}")
        return True

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "update_profile",
                "update_from": update_from
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        return False


def handle_successful_refresh(
    member_info: Dict[str, Any],
    state_manager: Any
) -> Optional[str]:
    """Handle successful refresh through state validation"""
    try:
        # Validate member info
        if not isinstance(member_info, dict):
            raise StateException("Invalid member info format")

        # Extract dashboard data
        dashboard_data = member_info.get("data", {}).get("dashboard")
        if not dashboard_data:
            raise StateException("Missing dashboard data")

        # Structure profile data through validation
        profile_data = _structure_profile_data(
            member_info,
            state_manager,
            "refresh"
        )
        if not profile_data:
            raise StateException("Failed to structure profile data")

        # Update profile data
        profile_data["dashboard"] = dashboard_data

        # Update state through validation
        success, error = state_manager.update_state({
            "flow_data": {"data": profile_data}
        })
        if not success:
            raise StateException(f"Failed to update profile: {error}")

        # Handle account setup
        if not _handle_account_setup(dashboard_data, state_manager):
            raise StateException("Failed to set up accounts")

        logger.info("Successfully refreshed member info")
        return None

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={"operation": "handle_refresh"}
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        return str(e)
