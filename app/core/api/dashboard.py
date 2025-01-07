"""Dashboard state management

This module handles dashboard updates from API responses.
All API responses that include dashboard data should flow through here.
Dashboard data is the source of truth for member state.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import FlowException

logger = logging.getLogger(__name__)


def update_dashboard_from_response(
    api_response: Dict[str, Any],
    state_manager: Any,
    auth_token: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Update dashboard state from API response

    This is the main entry point for handling API responses that contain
    dashboard data. All API calls that return dashboard data should route
    through here to maintain consistent state.

    Args:
        api_response: Full API response containing dashboard data
        state_manager: State manager instance
        auth_token: Optional auth token from response

    Returns:
        Tuple[bool, Optional[str]]: Success flag and optional error message
    """
    try:
        # Validate response format
        if not isinstance(api_response, dict):
            raise FlowException(
                message="Invalid API response format",
                step="dashboard",
                action="validate_response",
                data={"response": api_response}
            )

        # Get and validate dashboard data
        dashboard_data = api_response.get("data", {}).get("dashboard")
        if not dashboard_data:
            raise FlowException(
                message="Missing dashboard data",
                step="dashboard",
                action="validate_dashboard",
                data={"response": api_response}
            )

        # Validate member data exists
        if not dashboard_data.get("member", {}).get("memberID"):
            raise FlowException(
                message="Missing member ID in dashboard",
                step="dashboard",
                action="validate_member",
                data={"dashboard": dashboard_data}
            )

        # Handle account setup
        if not _handle_account_setup(dashboard_data, state_manager):
            raise FlowException(
                message="Failed to set up accounts",
                step="dashboard",
                action="setup_accounts",
                data={"dashboard": dashboard_data}
            )

        # Structure action data
        action = api_response.get("data", {}).get("action", {})
        action_data = {
            "action": {
                "id": action.get("id", ""),
                "type": action.get("type", ""),
                "timestamp": datetime.utcnow().isoformat(),
                "actor": state_manager.get_channel_id() or "unknown",
                "details": action.get("details", {}),
                "message": _get_action_message(action),
                "status": action.get("status", "")
            }
        }

        # Update state with dashboard and flow data
        state_update = {
            "flow_data": {
                "data": action_data,
                "auth": {"token": auth_token} if auth_token else {}
            }
        }

        try:
            state_manager.update_state(state_update)
        except Exception as e:
            raise FlowException(
                message="Failed to update state",
                step="dashboard",
                action="update_state",
                data={"error": str(e), "update": state_update}
            )

        logger.info("Successfully updated dashboard state")
        return True, None

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "step": "dashboard",
                "action": "update_dashboard"
            }
        )
        ErrorHandler.handle_flow_error(
            step=error_context.details["step"],
            action=error_context.details["action"],
            data={},
            message=error_context.message,
            flow_state={}
        )
        return False, str(e)


def _handle_account_setup(
    dashboard_data: Dict[str, Any],
    state_manager: Any
) -> bool:
    """Handle account setup through state validation"""
    try:
        # Find the PERSONAL account (API guarantees one per member)
        accounts = dashboard_data.get("accounts", [])
        personal_account = next(
            (acc for acc in accounts if acc.get("accountType") == "PERSONAL"),
            None
        )

        if not personal_account:
            raise FlowException(
                message="No PERSONAL account found in dashboard",
                step="dashboard",
                action="setup_account",
                data={"accounts": accounts}
            )

        # Store dashboard and active account ID
        state_update = {
            "dashboard": dashboard_data,  # Complete API response is the truth
            "active_account_id": personal_account["accountID"]  # Always set to PERSONAL account
        }

        try:
            state_manager.update_state(state_update)
        except Exception as e:
            raise FlowException(
                message="Failed to update account state",
                step="dashboard",
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
                "step": "dashboard",
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


def _get_action_message(action: Dict[str, Any]) -> str:
    """Get action message from response"""
    # Return explicit message if present
    if action.get("message"):
        return action["message"]

    # Check details for message
    if action.get("details", {}).get("message"):
        return action["details"]["message"]

    return ""
