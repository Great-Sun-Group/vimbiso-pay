"""CredEx service using pure functions with strict state validation"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException

from .auth import login as auth_login
from .auth import register_member as auth_register
from .member import refresh_member_info as member_refresh_info
from .member import validate_account_handle as member_validate_handle
from .offers import get_credex, offer_credex

logger = logging.getLogger(__name__)


def get_credex_service(state_manager: Any) -> Dict[str, Any]:
    """Get CredEx service functions with strict state validation"""
    # Let StateManager validate through state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": "credex",
            "step": 0,
            "current_step": "init"
        }
    })

    # Return service functions that need state
    return {
        'validate_account_handle': lambda handle: validate_member_handle(state_manager, handle),
        'get_credex': lambda credex_id: get_credex(credex_id, state_manager.get("jwt_token")),
        'offer_credex': lambda data: offer_credex(data, state_manager.get("jwt_token"))
    }


def handle_registration(state_manager: Any, member_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Handle member registration with strict state validation"""
    try:
        # Let StateManager validate through state update
        state_manager.update_state({
            "flow_data": {
                "registration": member_data
            }
        })

        # Let StateManager validate internally
        success, result = auth_register(member_data, state_manager.get("channel")["identifier"])
        logger.info("Registration attempt completed")
        return success, result

    except StateException as e:
        logger.error(f"Registration error: {str(e)}")
        return False, {"message": str(e)}


def update_member_state(state_manager: Any, result: Dict[str, Any]) -> None:
    """Update member state from API response"""
    data = result.get("data", {})
    action = data.get("action", {})
    details = action.get("details", {})
    dashboard = data.get("dashboard", {})

    # Only update state if dashboard has data (empty for simple endpoints)
    if dashboard.get("member") or dashboard.get("accounts"):
        state_manager.update_state({
            # Auth data
            "jwt_token": details.get("token"),
            "authenticated": True,
            "member_id": details.get("memberID"),
            # Member data
            "member_data": dashboard.get("member"),
            # Account data
            "accounts": dashboard.get("accounts", []),
            "active_account_id": next(
                (account["accountID"] for account in dashboard.get("accounts", [])
                 if account["accountType"] == "PERSONAL"),
                None
            )
        })
    # Always update token if present
    elif details.get("token"):
        state_manager.update_state({
            "jwt_token": details.get("token")
        })


def handle_login(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Handle login with strict state validation"""
    try:
        # Initial login just needs phone number
        success, result = auth_login(state_manager.get("channel")["identifier"])
        if not success:
            return False, result

        # Extract auth data from response
        data = result.get("data", {})
        action = data.get("action", {})

        # Verify login succeeded
        if action.get("type") != "MEMBER_LOGIN":
            return False, {
                "message": "Invalid login response"
            }

        # Update complete member state
        update_member_state(state_manager, result)

        logger.info("Login completed and state updated")
        return True, result

    except StateException as e:
        logger.error(f"Login error: {str(e)}")
        return False, {"message": str(e)}


def validate_member_handle(state_manager: Any, handle: str) -> Tuple[bool, Dict[str, Any]]:
    """Validate member handle (simple endpoint, no state update needed)"""
    try:
        # Simple validation endpoint - just return result
        return member_validate_handle(handle, state_manager.get("jwt_token"))

    except StateException as e:
        error_msg = str(e)
        logger.error(f"Handle validation error: {error_msg}")
        return False, {"message": error_msg}


def refresh_member_info(state_manager: Any) -> Optional[str]:
    """Refresh member info with dashboard data"""
    try:
        # Get fresh member info
        result = member_refresh_info(state_manager.get("channel")["identifier"])
        if isinstance(result, str):  # Error case
            return result

        # Update state with fresh dashboard data
        update_member_state(state_manager, result)
        return None

    except StateException as e:
        error_msg = str(e)
        logger.error(f"Member refresh validation error: {error_msg}")
        return error_msg
