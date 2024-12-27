"""Main API client using pure functions"""
import logging
from typing import Dict, Callable

from services.whatsapp.types import BotServiceInterface
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


def create_api_service(bot_service: BotServiceInterface) -> Dict[str, Callable]:
    """Create API service with all available operations

    Args:
        bot_service: Bot service instance with state management

    Returns:
        Dictionary of API operations
    """
    return {
        # Auth operations
        "login": lambda: auth_login(bot_service.user.channel_identifier),
        "register_member": lambda member_data: auth_register(member_data, bot_service.user.state_manager.get("jwt_token")),

        # Dashboard operations
        "get_dashboard": lambda: get_member_dashboard(
            bot_service.user.channel_identifier,
            bot_service.user.state_manager.get("jwt_token")
        ),
        "refresh_member_info": lambda reset=True, silent=True, init=False: refresh_member(
            bot_service,
            reset,
            silent,
            init
        ),
        "validate_handle": lambda handle: validate_member_handle(
            handle,
            bot_service.user.state_manager.get("jwt_token")
        ),
        "get_ledger": lambda payload: get_member_ledger(
            payload,
            bot_service.user.state_manager.get("jwt_token")
        ),

        # CredEx operations
        "offer_credex": lambda offer_data: offer_credex(
            bot_service,
            offer_data
        ),
        "accept_credex": lambda credex_id: accept_credex(
            bot_service,
            credex_id
        ),
        "decline_credex": lambda credex_id: decline_credex(
            bot_service,
            credex_id
        ),
        "cancel_credex": lambda credex_id: cancel_credex(
            bot_service,
            credex_id
        ),
        "get_credex": lambda credex_id: get_credex(
            bot_service,
            credex_id
        ),
        "accept_bulk_credex": lambda credex_ids: accept_bulk_credex(
            bot_service,
            credex_ids
        ),

        # Profile operations
        "update_profile_from_response": lambda api_response, action_type, update_from, token=None: update_profile_from_response(
            api_response,
            bot_service.user.state_manager,
            action_type,
            update_from,
            token
        ),
    }
