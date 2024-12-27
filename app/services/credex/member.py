"""CredEx member operations using pure functions"""
import logging
from typing import Any, Dict, Optional, Tuple

from .base import make_credex_request
from .exceptions import ValidationError
from core.utils.state_validator import StateValidator

logger = logging.getLogger(__name__)


def get_dashboard(state_manager: Any, phone: str) -> Tuple[bool, Dict[str, Any]]:
    """Get dashboard information"""
    if not state_manager:
        raise ValueError("State manager is required")
    if not phone:
        raise ValidationError("Phone number is required")

    try:
        response = make_credex_request(
            'member', 'get_dashboard',
            payload={"phone": phone}
        )
        data = response.json()

        # Extract dashboard data
        if dashboard := data.get("data", {}).get("dashboard"):
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {"profile": state_manager.get("profile")},
                {"profile"}
            )
            if validation.is_valid:
                # Update state with dashboard data
                state_manager.update({
                    "profile": {
                        **state_manager.get("profile", {}),
                        "dashboard": dashboard
                    }
                })
            return True, data
        return False, {"message": "No dashboard data received"}

    except Exception as e:
        logger.error(f"Dashboard fetch failed: {str(e)}")
        return False, {"message": str(e)}


def validate_handle(handle: str) -> Tuple[bool, Dict[str, Any]]:
    """Validate CredEx handle"""
    if not handle:
        raise ValidationError("Handle is required")

    try:
        response = make_credex_request(
            'member', 'validate_handle',
            payload={"accountHandle": handle.lower()}
        )
        data = response.json()

        # Extract account details
        if details := data.get("data", {}).get("action", {}).get("details"):
            if account_id := details.get("accountID"):
                return True, {
                    "data": {
                        "accountID": account_id,
                        "accountName": details.get("accountName", ""),
                        "accountHandle": handle
                    }
                }
        return False, {"message": "Account not found"}

    except Exception as e:
        logger.error(f"Handle validation failed: {str(e)}")
        return False, {"message": str(e)}


def refresh_member_info(
    state_manager: Any,
    phone: str,
    reset: bool = True,
    silent: bool = True,
    init: bool = False
) -> Optional[str]:
    """Refresh member information"""
    if not state_manager:
        raise ValueError("State manager is required")
    if not phone:
        raise ValidationError("Phone number is required")

    try:
        # Re-authenticate to get fresh data
        response = make_credex_request(
            'auth', 'login',
            payload={"phone": phone}
        )
        data = response.json()

        if token := (data.get("data", {})
                     .get("action", {})
                     .get("details", {})
                     .get("token")):
            # Update token in state
            state_manager.update({"jwt_token": token})
            return None
        return "Failed to refresh member info"

    except Exception as e:
        logger.error(f"Member info refresh failed: {str(e)}")
        return str(e)


def get_member_accounts(member_id: str) -> Tuple[bool, Dict[str, Any]]:
    """Get member accounts"""
    if not member_id:
        raise ValidationError("Member ID is required")

    try:
        response = make_credex_request(
            'member', 'get_accounts',
            payload={"memberID": member_id}
        )
        data = response.json()

        if accounts := data.get("data", {}).get("accounts"):
            return True, {"data": {"accounts": accounts}}
        return False, {"message": "No accounts found"}

    except Exception as e:
        logger.error(f"Failed to get member accounts: {str(e)}")
        return False, {"message": str(e)}
