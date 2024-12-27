"""CredEx service with strict state management using pure functions"""
import logging
from typing import Any, Dict, Optional, Tuple, Callable

from .auth import login as auth_login, register_member as auth_register
from .config import CredExConfig
from .member import (
    get_dashboard as member_get_dashboard,
    validate_handle as member_validate_handle,
    refresh_member_info as member_refresh_info,
    get_member_accounts as member_get_accounts,
)
from .offers import (
    offer_credex as create_offer,
    confirm_credex as confirm_offer,
    accept_credex as accept_offer,
    accept_bulk_credex as accept_bulk_offers,
    decline_credex as decline_offer,
    cancel_credex as cancel_offer,
    get_credex as get_offer,
    get_ledger as get_member_ledger,
)

logger = logging.getLogger(__name__)


def create_credex_service(
    get_token: Optional[Callable[[], Optional[str]]] = None,
    get_member_id: Optional[Callable[[], Optional[str]]] = None,
    get_channel: Optional[Callable[[], Optional[Dict[str, Any]]]] = None,
    on_token_update: Optional[Callable[[str], None]] = None,
    config: Optional[CredExConfig] = None,
) -> Dict[str, Any]:
    """Create CredEx service with state management functions

    Args:
        get_token: Function to get JWT token
        get_member_id: Function to get member ID
        get_channel: Function to get channel info
        on_token_update: Callback for token updates
        config: Service configuration

    Returns:
        Dict containing service functions and properties
    """
    config = config or CredExConfig.from_env()

    def get_jwt_token() -> Optional[str]:
        """Get JWT token enforcing SINGLE SOURCE OF TRUTH"""
        try:
            if not get_token:
                logger.warning("No token getter function provided")
                return None

            token = get_token()
            if not token:
                logger.debug("No token available")
                return None

            return token

        except Exception as e:
            logger.error(f"Token access error: {str(e)}")
            return None

    def get_member_identifier() -> Optional[str]:
        """Get member ID enforcing SINGLE SOURCE OF TRUTH"""
        try:
            if not get_member_id:
                logger.warning("No member ID getter function provided")
                return None

            member_id = get_member_id()
            if not member_id:
                logger.debug("No member ID available")
                return None

            return member_id

        except Exception as e:
            logger.error(f"Member ID access error: {str(e)}")
            return None

    def get_channel_info() -> Optional[Dict[str, Any]]:
        """Get channel info enforcing SINGLE SOURCE OF TRUTH"""
        try:
            if not get_channel:
                logger.warning("No channel getter function provided")
                return None

            channel = get_channel()
            if not channel:
                logger.debug("No channel info available")
                return None

            if not isinstance(channel, dict):
                raise ValueError("Invalid channel info format")

            return channel

        except Exception as e:
            logger.error(f"Channel info access error: {str(e)}")
            return None

    def validate_initialization() -> Optional[str]:
        """Validate service initialization enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate config
            if not config:
                return "Service configuration not initialized"

            # Validate state access functions
            if not get_token:
                logger.warning("No token getter function provided")
            if not get_member_id:
                logger.warning("No member ID getter function provided")
            if not get_channel:
                logger.warning("No channel getter function provided")

            logger.info("Service initialization validated successfully")
            return None

        except Exception as e:
            error_msg = f"Service validation error: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def service_login(phone: str) -> Tuple[bool, str]:
        """Authenticate user enforcing SINGLE SOURCE OF TRUTH"""
        try:
            if not phone:
                raise ValueError("Phone number is required")

            success, result = auth_login(phone, jwt_token=get_jwt_token())

            if success:
                logger.info(f"Login successful for phone {phone}")
                if token := result.get("token"):
                    if on_token_update:
                        on_token_update(token)
            else:
                logger.warning(f"Login failed for phone {phone}: {result.get('message')}")

            return success, result.get("message", str(result))

        except ValueError as e:
            logger.error(f"Login error: {str(e)}")
            return False, str(e)

    def service_register(member_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Register new member enforcing SINGLE SOURCE OF TRUTH"""
        try:
            if not isinstance(member_data, dict):
                raise ValueError("Member data must be a dictionary")
            if not member_data:
                raise ValueError("Member data is required")

            success, result = auth_register(member_data, get_channel_info()["identifier"], jwt_token=get_jwt_token())

            if success:
                logger.info("Member registration successful")
                if token := result.get("token"):
                    if on_token_update:
                        on_token_update(token)
            else:
                logger.warning(f"Member registration failed: {result.get('message')}")

            return success, result.get("message", str(result))

        except ValueError as e:
            logger.error(f"Registration error: {str(e)}")
            return False, str(e)

    # Return service interface
    return {
        # Properties
        "jwt_token": get_jwt_token,
        "member_id": get_member_identifier,
        "channel": get_channel_info,

        # Auth functions
        "login": service_login,
        "register_member": service_register,

        # Member functions
        "get_dashboard": lambda phone: member_get_dashboard(phone, jwt_token=get_jwt_token()),
        "validate_handle": lambda handle: member_validate_handle(handle, jwt_token=get_jwt_token()),
        "refresh_member_info": lambda phone, reset=True, silent=True, init=False: member_refresh_info(phone, reset, silent, init, jwt_token=get_jwt_token()),
        "get_member_accounts": lambda member_id: member_get_accounts(member_id, jwt_token=get_jwt_token()),

        # Offer functions
        "offer_credex": lambda data: create_offer(data, jwt_token=get_jwt_token()),
        "confirm_credex": lambda cid, aid: confirm_offer(cid, aid, jwt_token=get_jwt_token()),
        "accept_credex": lambda oid: accept_offer(oid, jwt_token=get_jwt_token()),
        "accept_bulk_credex": lambda oids: accept_bulk_offers(oids, jwt_token=get_jwt_token()),
        "decline_credex": lambda oid: decline_offer(oid, jwt_token=get_jwt_token()),
        "cancel_credex": lambda oid: cancel_offer(oid, jwt_token=get_jwt_token()),
        "get_credex": lambda oid: get_offer(oid, jwt_token=get_jwt_token()),
        "get_ledger": lambda mid: get_member_ledger(mid, jwt_token=get_jwt_token()),

        # Validation
        "validate_initialization": validate_initialization,
    }
