"""CredEx member operations with strict state validation"""
import logging
from typing import Any, Dict, Tuple

from core.utils.exceptions import StateException
from .base import make_credex_request

logger = logging.getLogger(__name__)


def get_dashboard(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get dashboard information"""
    try:
        # StateManager handles validation of phone and jwt_token
        response = make_credex_request(
            'member', 'get_dashboard',
            payload={"phone": state_manager.get("phone")},
            jwt_token=state_manager.get("jwt_token")
        )
        data = response.json()

        if not data.get("data", {}).get("dashboard"):
            raise StateException("No dashboard data received")

        return True, data

    except StateException:
        # Re-raise StateException for proper error propagation
        raise
    except Exception as e:
        logger.error(f"Dashboard fetch failed: {str(e)}")
        raise StateException(f"Dashboard fetch failed: {str(e)}")


def validate_handle(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Validate CredEx handle"""
    try:
        # StateManager handles validation of handle and jwt_token
        response = make_credex_request(
            'member', 'validate_handle',
            payload={"accountHandle": state_manager.get("handle")},
            jwt_token=state_manager.get("jwt_token")
        )
        data = response.json()

        details = data.get("data", {}).get("action", {}).get("details", {})
        if not details:
            raise StateException("Account not found")

        return True, {"data": details}

    except StateException:
        # Re-raise StateException for proper error propagation
        raise
    except Exception as e:
        logger.error(f"Handle validation failed: {str(e)}")
        raise StateException(f"Handle validation failed: {str(e)}")


def refresh_member_info(state_manager: Any) -> None:
    """Refresh member information"""
    try:
        # StateManager handles validation of phone
        response = make_credex_request(
            'auth', 'login',
            payload={"phone": state_manager.get("phone")}
        )
        data = response.json()

        if not data.get("data", {}).get("action", {}).get("details", {}).get("token"):
            raise StateException("Failed to refresh member info")

        return None

    except StateException:
        # Re-raise StateException for proper error propagation
        raise
    except Exception as e:
        logger.error(f"Member info refresh failed: {str(e)}")
        raise StateException(f"Member info refresh failed: {str(e)}")


def get_member_accounts(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get member accounts from state"""
    try:
        # StateManager handles validation
        personal_account = state_manager.get("personal_account")
        if not personal_account:
            raise StateException("Personal account data not found in state")

        return True, {
            "data": {
                "accounts": [personal_account]
            }
        }

    except StateException:
        # Re-raise StateException for proper error propagation
        raise
    except Exception as e:
        logger.error(f"Failed to get member accounts from state: {str(e)}")
        raise StateException(f"Failed to get member accounts: {str(e)}")
