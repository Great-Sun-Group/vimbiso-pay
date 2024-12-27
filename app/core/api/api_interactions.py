"""API interactions using pure functions"""
import logging
from typing import Optional, Callable, Dict, Any
from django.core.cache import cache

from services.whatsapp.types import BotServiceInterface
from core.utils.state_validator import StateValidator
from ..config.constants import CachedUser
from ..utils.utils import CredexWhatsappService

from .auth_client import login as auth_login, register_member as auth_register
from .dashboard_client import (
    get_dashboard as get_member_dashboard,
    validate_handle as validate_member_handle,
    get_ledger as get_member_ledger,
    process_dashboard_response,
)
from .credex import (
    offer_credex as create_credex,
    accept_credex as accept_credex_offer,
    accept_bulk_credex as accept_bulk_credex_offers,
    decline_credex as decline_credex_offer,
    cancel_credex as cancel_credex_offer,
    get_credex as get_credex_details,
)

logger = logging.getLogger(__name__)


def send_delay_message(bot_service: BotServiceInterface) -> None:
    """Sends a delay message to the user"""
    # Get required state fields with validation at boundary
    validation = StateValidator.validate_before_access(
        {
            "stage": bot_service.user.state_manager.get("stage"),
            "channel": bot_service.user.state_manager.get("channel")
        },
        {"stage", "channel"}
    )
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return

    stage = bot_service.user.state_manager.get("stage")
    channel = bot_service.user.state_manager.get("channel", {})
    channel_id = channel.get("identifier")

    if (
        stage != "handle_action_register"
        and not cache.get(f"{channel_id}_interracted")
    ):
        CredexWhatsappService(
            payload={
                "messaging_product": "whatsapp",
                "preview_url": False,
                "recipient_type": "individual",
                "to": channel_id,
                "type": "text",
                "text": {"body": "Please wait while we process your request..."},
            }
        ).send_message()
        cache.set(f"{channel_id}_interracted", True, 60 * 15)


def send_first_message(bot_service: BotServiceInterface) -> None:
    """Sends the first message to the user"""
    # Validate channel info at boundary
    validation = StateValidator.validate_before_access(
        {"channel": bot_service.user.state_manager.get("channel")},
        {"channel"}
    )
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return

    channel = bot_service.user.state_manager.get("channel", {})
    channel_id = channel.get("identifier")

    first_message = "Welcome to CredEx! How can I assist you today?"
    CredexWhatsappService(
        payload={
            "messaging_product": "whatsapp",
            "preview_url": False,
            "recipient_type": "individual",
            "to": channel_id,
            "type": "text",
            "text": {"body": first_message},
        }
    ).send_message()


def handle_reset_and_init(bot_service: BotServiceInterface, reset: bool, silent: bool, init: bool) -> None:
    """Handles reset and initialization logic"""
    if reset and not silent or init:
        send_delay_message(bot_service)
        send_first_message(bot_service)


def refresh_dashboard(bot_service: BotServiceInterface) -> Optional[Dict[str, Any]]:
    """Refreshes the member's dashboard"""
    logger.info("Refreshing dashboard")
    success, data = get_member_dashboard(
        bot_service.user.channel_identifier,
        bot_service.user.state_manager.get("jwt_token")
    )
    if success:
        user = CachedUser(bot_service.user.channel_identifier)
        # Get required state fields with validation at boundary
        required_fields = {"profile", "current_account", "jwt_token", "authenticated"}
        current_state = {
            field: user.state_manager.get(field)
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
    bot_service: BotServiceInterface,
    reset: bool = True,
    silent: bool = True,
    init: bool = False
) -> Optional[Dict[str, Any]]:
    """Refreshes member info by making an API call to CredEx"""
    logger.info("Refreshing member info")

    user = CachedUser(bot_service.user.channel_identifier)
    # Get required state fields with validation at boundary
    required_fields = {"profile", "current_account", "jwt_token", "authenticated"}
    current_state = {
        field: user.state_manager.get(field)
        for field in required_fields
    }

    # Validate at boundary
    validation = StateValidator.validate_state(current_state)
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return None

    handle_reset_and_init(bot_service, reset, silent, init)

    try:
        success, data = get_member_dashboard(
            bot_service.user.channel_identifier,
            bot_service.user.state_manager.get("jwt_token")
        )
        if not success:
            error_msg = data.get("message", "")
            if any(msg in error_msg for msg in [
                "Member not found",
                "Could not retrieve member dashboard",
                "Invalid token"
            ]):
                return bot_service.action_handler.handle_action_register(register=True)
            return None

        return process_dashboard_response(current_state, data)

    except Exception as e:
        logger.exception(f"Error during refresh: {str(e)}")
        return None


def create_api_interactions(bot_service: BotServiceInterface) -> Dict[str, Callable]:
    """Create API interactions service

    Args:
        bot_service: Bot service instance with state management

    Returns:
        Dictionary of API interaction functions
    """
    return {
        # Auth operations
        "login": lambda: auth_login(bot_service.user.channel_identifier),
        "register_member": lambda payload: auth_register(
            payload,
            bot_service.user.state_manager.get("jwt_token")
        ),

        # Dashboard operations
        "get_dashboard": lambda: get_member_dashboard(
            bot_service.user.channel_identifier,
            bot_service.user.state_manager.get("jwt_token")
        ),
        "refresh_dashboard": lambda: refresh_dashboard(bot_service),
        "refresh_member_info": lambda reset=True, silent=True, init=False: refresh_member_info(
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
        "offer_credex": lambda payload: create_credex(
            payload,
            bot_service.user.state_manager.get("jwt_token")
        ),
        "accept_credex": lambda payload: accept_credex_offer(
            payload,
            bot_service.user.state_manager.get("jwt_token")
        ),
        "accept_bulk_credex": lambda payload: accept_bulk_credex_offers(
            payload,
            bot_service.user.state_manager.get("jwt_token")
        ),
        "decline_credex": lambda payload: decline_credex_offer(
            payload,
            bot_service.user.state_manager.get("jwt_token")
        ),
        "cancel_credex": lambda payload: cancel_credex_offer(
            payload,
            bot_service.user.state_manager.get("jwt_token")
        ),
        "get_credex": lambda payload: get_credex_details(
            payload,
            bot_service.user.state_manager.get("jwt_token")
        ),
    }
