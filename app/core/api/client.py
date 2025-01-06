"""Main API client using pure functions"""
import logging
from typing import Any, Callable, Dict

from .auth import login as auth_login
from .auth import register_member as auth_register
from .credex import (accept_bulk_credex, accept_credex, cancel_credex,
                     decline_credex, get_credex, offer_credex)
from .credex import get_ledger as get_account_ledger
from .credex import validate_account_handle as validate_member_handle
from .profile import update_profile_from_response

logger = logging.getLogger(__name__)


def create_api_service(state_manager: Any, channel_id: str) -> Dict[str, Callable]:
    """Create API service with all available operations

    Args:
        state_manager: State manager instance
        channel_id: Channel identifier

    Returns:
        Dict[str, Callable]: Dictionary of API operations
    """
    return {
        # Auth operations
        "login": lambda: auth_login(channel_id),
        "register_member": lambda member_data: auth_register(
            member_data,
            state_manager.get_flow_data().get("auth", {}).get("token")
        ),

        # Account operations
        "validate_account_handle": lambda handle: validate_member_handle(
            handle,
            state_manager.get_flow_data().get("auth", {}).get("token")
        ),
        "get_account_ledger": lambda account_id: get_account_ledger(
            {"accountID": account_id},
            state_manager.get_flow_data().get("auth", {}).get("token")
        ),

        # CredEx operations
        "offer_credex": lambda: offer_credex(state_manager),
        "accept_credex": lambda: accept_credex(state_manager),
        "decline_credex": lambda: decline_credex(state_manager),
        "cancel_credex": lambda: cancel_credex(state_manager),
        "get_credex": lambda: get_credex(state_manager),
        "accept_bulk_credex": lambda: accept_bulk_credex(state_manager),

        # Profile operations
        "update_profile_from_response": lambda api_response, action_type, update_from, token=None: update_profile_from_response(
            api_response,
            state_manager,
            action_type,
            update_from,
            token
        ),
    }
