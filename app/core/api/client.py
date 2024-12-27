"""Main API client using pure functions"""
import logging
from typing import Any, Dict, Callable

from .auth import login as auth_login, register_member as auth_register
from .credex import (
    offer_credex,
    accept_credex,
    decline_credex,
    cancel_credex,
    get_credex,
    accept_bulk_credex,
)
from .dashboard import (
    get_dashboard as get_member_dashboard,
    refresh_member_info as refresh_member,
    validate_handle as validate_member_handle,
    get_ledger as get_member_ledger,
)
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
        "register_member": lambda member_data: auth_register(member_data, state_manager.get("jwt_token")),

        # Dashboard operations
        "get_dashboard": lambda: get_member_dashboard(
            channel_id,
            state_manager.get("jwt_token")
        ),
        "refresh_member_info": lambda reset=True, silent=True, init=False: refresh_member(
            state_manager,
            channel_id,
            reset,
            silent,
            init
        ),
        "validate_handle": lambda handle: validate_member_handle(
            handle,
            state_manager.get("jwt_token")
        ),
        "get_ledger": lambda payload: get_member_ledger(
            payload,
            state_manager.get("jwt_token")
        ),

        # CredEx operations
        "offer_credex": lambda offer_data: offer_credex(
            state_manager,
            channel_id,
            offer_data
        ),
        "accept_credex": lambda credex_id: accept_credex(
            state_manager,
            channel_id,
            credex_id
        ),
        "decline_credex": lambda credex_id: decline_credex(
            state_manager,
            channel_id,
            credex_id
        ),
        "cancel_credex": lambda credex_id: cancel_credex(
            state_manager,
            channel_id,
            credex_id
        ),
        "get_credex": lambda credex_id: get_credex(
            state_manager,
            channel_id,
            credex_id
        ),
        "accept_bulk_credex": lambda credex_ids: accept_bulk_credex(
            state_manager,
            channel_id,
            credex_ids
        ),

        # Profile operations
        "update_profile_from_response": lambda api_response, action_type, update_from, token=None: update_profile_from_response(
            api_response,
            state_manager,
            action_type,
            update_from,
            token
        ),
    }
