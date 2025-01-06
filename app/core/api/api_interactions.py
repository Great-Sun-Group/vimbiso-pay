"""API interactions using pure functions"""
import logging
from typing import Any, Callable, Dict, Optional

from .auth_client import login as auth_login
from .auth_client import onboard_member as auth_onboard
from .credex import accept_bulk_credex as accept_bulk_credex_offers
from .credex import accept_credex as accept_credex_offer
from .credex import cancel_credex as cancel_credex_offer
from .credex import decline_credex as decline_credex_offer
from .credex import get_credex as get_credex_details
from .credex import get_ledger as get_account_ledger
from .credex import offer_credex as create_credex
from .credex import validate_account_handle as validate_member_handle

logger = logging.getLogger(__name__)


def process_dashboard_response(current_state: Dict[str, Any], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process dashboard response with state validation

    Args:
        current_state: Current state fields
        data: Dashboard response data

    Returns:
        Processed dashboard data or None if invalid
    """
    try:
        # Validate response format
        if not isinstance(data, dict):
            logger.error("Invalid dashboard data format")
            return None

        dashboard_data = data.get("data", {}).get("dashboard")
        member_details = data.get("data", {}).get("action", {}).get("details", {})

        if not dashboard_data or not member_details:
            logger.error("Missing required dashboard data")
            return None

        # Return validated response
        return {
            "data": {
                "dashboard": dashboard_data,
                "action": {
                    "details": member_details
                }
            }
        }

    except Exception:
        logger.exception("Error processing dashboard response")
        return None


def create_api_interactions(state_manager: Any, channel_id: str) -> Dict[str, Callable]:
    """Create API interactions service with pure functions

    Args:
        state_manager: State manager instance
        channel_id: Channel identifier

    Returns:
        Dict[str, Callable]: Dictionary of API interaction functions
    """
    return {
        # Auth operations
        "login": lambda: auth_login(channel_id),
        "onboard_member": lambda payload: auth_onboard(
            payload,
            state_manager.get("jwt_token")
        ),

        "validate_account_handle": lambda handle: validate_member_handle(
            handle,
            state_manager.get("jwt_token")
        ),
        "get_account_ledger": lambda account_id: get_account_ledger(
            {"accountID": account_id},
            state_manager.get("jwt_token")
        ),

        # CredEx operations
        "offer_credex": lambda: create_credex(state_manager),
        "accept_credex": lambda: accept_credex_offer(state_manager),
        "accept_bulk_credex": lambda: accept_bulk_credex_offers(state_manager),
        "decline_credex": lambda: decline_credex_offer(state_manager),
        "cancel_credex": lambda: cancel_credex_offer(state_manager),
        "get_credex": lambda: get_credex_details(state_manager),
    }
