"""CredEx member operations with strict state validation"""
import logging
from typing import Any, Dict, Tuple

from core.utils.exceptions import StateException

from .base import make_credex_request

logger = logging.getLogger(__name__)


def get_member_accounts(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get member accounts from state enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Let StateManager validate through update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "accounts",
                "step": 0,
                "current_step": "fetch"
            }
        })

        # Get accounts from state (StateManager validates)
        accounts = state_manager.get("accounts")
        active_id = state_manager.get("active_account_id")

        return True, {
            "data": {
                "accounts": accounts,
                "active_account_id": active_id
            }
        }

    except StateException:
        # Re-raise StateException for proper error propagation
        raise


def validate_account_handle(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Validate CredEx handle enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Let StateManager validate through update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "handle_validation",
                "step": 0,
                "current_step": "validate",
                "data": {
                    "handle": state_manager.get("handle")
                }
            }
        })

        # Make API request (StateManager validates jwt_token)
        response = make_credex_request(
            'member', 'validate_account_handle',
            payload={"accountHandle": state_manager.get("handle")},
            jwt_token=state_manager.get("jwt_token")
        )

        # Let StateManager validate response through update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "handle_validation",
                "step": 1,
                "current_step": "complete",
                "data": {
                    "validation": response.json()
                }
            }
        })

        return True, response.json()

    except StateException:
        # Re-raise StateException for proper error propagation
        raise


def refresh_member_info(state_manager: Any) -> None:
    """Refresh member information enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Let StateManager validate through update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "refresh",
                "step": 0,
                "current_step": "start"
            }
        })

        # Make API request (StateManager validates channel)
        response = make_credex_request(
            'auth', 'login',
            payload={"phone": state_manager.get("channel")["identifier"]}
        )

        # Let StateManager validate response through update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "refresh",
                "step": 1,
                "current_step": "complete",
                "data": {
                    "refresh": response.json()
                }
            }
        })

        return None

    except StateException:
        # Re-raise StateException for proper error propagation
        raise
