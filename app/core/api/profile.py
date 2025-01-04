"""Profile and state management through validation"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import FlowException

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
            raise FlowException(
                message="Channel required for profile update",
                step="profile",
                action="validate",
                data={"channel": channel}
            )

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
            error_type="flow",
            message=str(e),
            details={
                "step": "profile",
                "action": "structure_data",
                "action_type": action_type
            }
        )
        ErrorHandler.handle_flow_error(
            step=error_context.details["step"],
            action=error_context.details["action"],
            data={"action_type": error_context.details["action_type"]},
            message=error_context.message,
            flow_state={}
        )
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
            raise FlowException(
                message="No valid accounts found",
                step="profile",
                action="validate_accounts",
                data={"accounts": accounts}
            )

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
            raise FlowException(
                message="No valid accounts after processing",
                step="profile",
                action="process_accounts",
                data={"processed": processed_accounts}
            )

        # Find personal account through validation
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise FlowException(
                message="Channel required for account setup",
                step="profile",
                action="setup_account",
                data={"channel": channel}
            )

        # Prioritize personal account, fallback to channel match
        personal_account = next(
            (acc for acc in processed_accounts if acc["accountType"] == "PERSONAL"),
            next(
                (acc for acc in processed_accounts if acc["accountHandle"] == channel["identifier"]),
                None
            )
        )

        if not personal_account:
            raise FlowException(
                message="No valid personal account found",
                step="profile",
                action="find_account",
                data={"accounts": processed_accounts}
            )

        # Update state through validation
        state_update = {
            "accounts": processed_accounts,  # Store all accounts at top level
            "active_account_id": personal_account["accountID"]  # Reference by ID
        }

        try:
            state_manager.update_state(state_update)
        except Exception as e:
            raise FlowException(
                message="Failed to update account state",
                step="profile",
                action="update_state",
                data={"error": str(e), "update": state_update}
            )

        logger.info(f"Successfully set up account: {personal_account['accountHandle']}")
        return True

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "step": "profile",
                "action": "setup_account"
            }
        )
        ErrorHandler.handle_flow_error(
            step=error_context.details["step"],
            action=error_context.details["action"],
            data={},
            message=error_context.message,
            flow_state={}
        )
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
            raise FlowException(
                message="Invalid API response format",
                step="profile",
                action="validate_response",
                data={"response": api_response}
            )

        # Structure profile data through validation
        profile_data = _structure_profile_data(
            api_response,
            state_manager,
            action_type
        )
        if not profile_data:
            raise FlowException(
                message="Failed to structure profile data",
                step="profile",
                action="structure_data",
                data={"profile": profile_data}
            )

        # Prepare state update
        state_update = {"flow_data": {"data": profile_data}}

        # Add token if provided
        if token:
            state_update["jwt_token"] = token

        # Update state through validation
        try:
            state_manager.update_state(state_update)
        except Exception as e:
            raise FlowException(
                message="Failed to update state",
                step="profile",
                action="update_state",
                data={"error": str(e), "update": state_update}
            )

        # Handle account setup if needed
        dashboard_data = api_response.get("data", {}).get("dashboard")
        if dashboard_data:
            if not _handle_account_setup(dashboard_data, state_manager):
                raise FlowException(
                    message="Failed to set up accounts",
                    step="profile",
                    action="setup_accounts",
                    data={"dashboard": dashboard_data}
                )

        logger.info(f"State updated from {update_from}")
        return True

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "step": "profile",
                "action": "update_profile",
                "update_from": update_from
            }
        )
        ErrorHandler.handle_flow_error(
            step=error_context.details["step"],
            action=error_context.details["action"],
            data={"update_from": error_context.details["update_from"]},
            message=error_context.message,
            flow_state={}
        )
        return False


def handle_successful_refresh(
    member_info: Dict[str, Any],
    state_manager: Any
) -> Optional[str]:
    """Handle successful refresh through state validation"""
    try:
        # Validate member info
        if not isinstance(member_info, dict):
            raise FlowException(
                message="Invalid member info format",
                step="profile",
                action="validate_member",
                data={"member_info": member_info}
            )

        # Extract dashboard data
        dashboard_data = member_info.get("data", {}).get("dashboard")
        if not dashboard_data:
            raise FlowException(
                message="Missing dashboard data",
                step="profile",
                action="validate_dashboard",
                data={"dashboard": dashboard_data}
            )

        # Structure profile data through validation
        profile_data = _structure_profile_data(
            member_info,
            state_manager,
            "refresh"
        )
        if not profile_data:
            raise FlowException(
                message="Failed to structure profile data",
                step="profile",
                action="structure_data",
                data={"profile": profile_data}
            )

        # Update profile data
        profile_data["dashboard"] = dashboard_data

        # Update state through validation
        try:
            state_manager.update_state({
                "flow_data": {"data": profile_data}
            })
        except Exception as e:
            raise FlowException(
                message="Failed to update profile",
                step="profile",
                action="update_profile",
                data={"error": str(e), "profile": profile_data}
            )

        # Handle account setup
        if not _handle_account_setup(dashboard_data, state_manager):
            raise FlowException(
                message="Failed to set up accounts",
                step="profile",
                action="setup_accounts",
                data={"dashboard": dashboard_data}
            )

        logger.info("Successfully refreshed member info")
        return None

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "step": "profile",
                "action": "handle_refresh"
            }
        )
        ErrorHandler.handle_flow_error(
            step=error_context.details["step"],
            action=error_context.details["action"],
            data={},
            message=error_context.message,
            flow_state={}
        )
        return str(e)
