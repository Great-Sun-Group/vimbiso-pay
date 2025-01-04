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
                step="profile",
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

        # Get dashboard data
        dashboard_data = api_response.get("data", {}).get("dashboard")
        if not dashboard_data:
            raise FlowException(
                message="Missing dashboard data",
                step="profile",
                action="validate_dashboard",
                data={"response": api_response}
            )

        # Handle account setup first to establish core state
        if not _handle_account_setup(dashboard_data, state_manager):
            raise FlowException(
                message="Failed to set up accounts",
                step="profile",
                action="setup_accounts",
                data={"dashboard": dashboard_data}
            )

        # Structure action data only (dashboard already in state)
        action_data = {
            "action": {
                "id": api_response.get("data", {}).get("action", {}).get("id", ""),
                "type": action_type,
                "timestamp": datetime.now().isoformat(),
                "actor": state_manager.get_channel_id() or "unknown",
                "details": api_response.get("data", {}).get("action", {}).get("details", {}),
                "message": _get_action_message(
                    api_response.get("data", {}).get("action", {}),
                    action_type
                ),
                "status": api_response.get("data", {}).get("action", {}).get("status", "")
            }
        }

        # Get member ID from dashboard (source of truth)
        member_id = dashboard_data.get("member", {}).get("memberID")
        if not member_id:
            raise FlowException(
                message="Missing member ID in dashboard",
                step="profile",
                action="validate_member",
                data={"dashboard": dashboard_data}
            )

        # Update state with core identity at top level (SINGLE SOURCE OF TRUTH)
        state_update = {
            "member_id": member_id,  # Member ID at top level
            "jwt_token": token if token else None,  # JWT token at top level
            "flow_data": {
                "flow_type": "profile",
                "step": "update_profile",
                "data": action_data
            }
        }

        try:
            state_manager.update_state(state_update)
        except Exception as e:
            raise FlowException(
                message="Failed to update state",
                step="profile",
                action="update_state",
                data={"error": str(e), "update": state_update}
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

        # Handle account setup first to establish core state
        if not _handle_account_setup(dashboard_data, state_manager):
            raise FlowException(
                message="Failed to set up accounts",
                step="profile",
                action="setup_accounts",
                data={"dashboard": dashboard_data}
            )

        # Structure action data only (dashboard already in state)
        action_data = {
            "action": {
                "id": member_info.get("data", {}).get("action", {}).get("id", ""),
                "type": "refresh",
                "timestamp": datetime.now().isoformat(),
                "actor": state_manager.get_channel_id() or "unknown",
                "details": member_info.get("data", {}).get("action", {}).get("details", {}),
                "message": _get_action_message(
                    member_info.get("data", {}).get("action", {}),
                    "refresh"
                ),
                "status": member_info.get("data", {}).get("action", {}).get("status", "")
            }
        }

        # Get member ID from dashboard (source of truth)
        member_id = dashboard_data.get("member", {}).get("memberID")
        if not member_id:
            raise FlowException(
                message="Missing member ID in dashboard",
                step="profile",
                action="validate_member",
                data={"dashboard": dashboard_data}
            )

        # Update state with core identity at top level (SINGLE SOURCE OF TRUTH)
        try:
            state_manager.update_state({
                "member_id": member_id,  # Member ID at top level
                "flow_data": {
                    "flow_type": "profile",
                    "step": "refresh_profile",
                    "data": action_data
                }
            })
        except Exception as e:
            raise FlowException(
                message="Failed to update state",
                step="profile",
                action="update_state",
                data={"error": str(e), "update": action_data}
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
