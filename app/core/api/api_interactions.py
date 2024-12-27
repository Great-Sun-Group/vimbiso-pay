"""API interactions using pure functions"""
import logging
from typing import Any, Callable, Dict, Optional

from core.utils.state_validator import StateValidator
from django.core.cache import cache

from ..utils.utils import send_whatsapp_message
from .auth_client import login as auth_login
from .auth_client import register_member as auth_register
from .credex import accept_bulk_credex as accept_bulk_credex_offers
from .credex import accept_credex as accept_credex_offer
from .credex import cancel_credex as cancel_credex_offer
from .credex import decline_credex as decline_credex_offer
from .credex import get_credex as get_credex_details
from .credex import offer_credex as create_credex
from .dashboard_client import get_dashboard as get_member_dashboard
from .dashboard_client import get_ledger as get_member_ledger
from .dashboard_client import process_dashboard_response
from .dashboard_client import validate_handle as validate_member_handle

logger = logging.getLogger(__name__)


def send_delay_message(state_manager: Any) -> None:
    """Sends a delay message to the user"""
    # Get required state fields with validation at boundary
    validation = StateValidator.validate_before_access(
        {
            "stage": state_manager.get("stage"),
            "channel": state_manager.get("channel")
        },
        {"stage", "channel"}
    )
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return

    stage = state_manager.get("stage")
    channel = state_manager.get("channel", {})
    channel_id = channel.get("identifier")

    if (
        stage != "handle_action_register"
        and not cache.get(f"{channel_id}_interracted")
    ):
        send_whatsapp_message(payload={
            "messaging_product": "whatsapp",
            "preview_url": False,
            "recipient_type": "individual",
            "to": channel_id,
            "type": "text",
            "text": {"body": "Please wait while we process your request..."},
        })
        cache.set(f"{channel_id}_interracted", True, 60 * 15)


def send_first_message(state_manager: Any) -> None:
    """Sends the first message to the user"""
    # Validate channel info at boundary
    validation = StateValidator.validate_before_access(
        {"channel": state_manager.get("channel")},
        {"channel"}
    )
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return

    channel = state_manager.get("channel", {})
    channel_id = channel.get("identifier")

    first_message = "Welcome to CredEx! How can I assist you today?"
    send_whatsapp_message(payload={
        "messaging_product": "whatsapp",
        "preview_url": False,
        "recipient_type": "individual",
        "to": channel_id,
        "type": "text",
        "text": {"body": first_message},
    })


def handle_reset_and_init(state_manager: Any, reset: bool, silent: bool, init: bool) -> None:
    """Handles reset and initialization logic"""
    if reset and not silent or init:
        send_delay_message(state_manager)
        send_first_message(state_manager)


def refresh_dashboard(state_manager: Any, channel_id: str) -> Optional[Dict[str, Any]]:
    """Refreshes the member's dashboard"""
    logger.info("Refreshing dashboard")
    success, data = get_member_dashboard(
        channel_id,
        state_manager.get("jwt_token")
    )
    if success:
        # Get required state fields with validation at boundary
        required_fields = {"profile", "current_account", "jwt_token", "authenticated"}
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        # Validate at boundary
        validation = StateValidator.validate_state(current_state)
        if not validation.is_valid:
            logger.error(f"Invalid state: {validation.error_message}")
            return None
        return process_dashboard_response(current_state, data)
    return None


def refresh_member_info(
    state_manager: Any,
    channel_id: str,
    reset: bool = True,
    silent: bool = True,
    init: bool = False
) -> Optional[Dict[str, Any]]:
    """Refreshes member info by making an API call to CredEx"""
    logger.info("Refreshing member info")

    # Get required state fields with validation at boundary
    required_fields = {"profile", "current_account", "jwt_token", "authenticated"}
    current_state = {
        field: state_manager.get(field)
        for field in required_fields
    }

    # Validate at boundary
    validation = StateValidator.validate_state(current_state)
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return None

    handle_reset_and_init(state_manager, reset, silent, init)

    try:
        success, data = get_member_dashboard(
            channel_id,
            state_manager.get("jwt_token")
        )
        if not success:
            error_msg = data.get("message", "")
            if any(msg in error_msg for msg in [
                "Member not found",
                "Could not retrieve member dashboard",
                "Invalid token"
            ]):
                return None  # Let caller handle registration
            return None

        return process_dashboard_response(current_state, data)

    except Exception as e:
        logger.exception(f"Error during refresh: {str(e)}")
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
        "register_member": lambda payload: auth_register(
            payload,
            state_manager.get("jwt_token")
        ),

        # Dashboard operations
        "get_dashboard": lambda: get_member_dashboard(
            channel_id,
            state_manager.get("jwt_token")
        ),
        "refresh_dashboard": lambda: refresh_dashboard(state_manager, channel_id),
        "refresh_member_info": lambda reset=True, silent=True, init=False: refresh_member_info(
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
        "offer_credex": lambda payload: create_credex(
            payload,
            state_manager.get("jwt_token")
        ),
        "accept_credex": lambda payload: accept_credex_offer(
            payload,
            state_manager.get("jwt_token")
        ),
        "accept_bulk_credex": lambda payload: accept_bulk_credex_offers(
            payload,
            state_manager.get("jwt_token")
        ),
        "decline_credex": lambda payload: decline_credex_offer(
            payload,
            state_manager.get("jwt_token")
        ),
        "cancel_credex": lambda payload: cancel_credex_offer(
            payload,
            state_manager.get("jwt_token")
        ),
        "get_credex": lambda payload: get_credex_details(
            payload,
            state_manager.get("jwt_token")
        ),
    }
