"""CredEx service using pure functions with strict state validation"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException
from core.utils.state_validator import StateValidator

from .auth import login as auth_login
from .auth import register_member as auth_register
from .member import get_dashboard as member_get_dashboard
from .member import get_member_accounts as member_get_accounts
from .member import refresh_member_info as member_refresh_info
from .member import validate_handle as member_validate_handle
from .offers import offer_credex, get_credex

logger = logging.getLogger(__name__)


def get_credex_service(state_manager: Any) -> Dict[str, Any]:
    """Get CredEx service functions with strict state validation"""
    # Validate required state upfront
    validation = StateValidator.validate_before_access(
        state_manager,
        {"member_id", "jwt_token", "account_id"}
    )
    if not validation.is_valid:
        raise ValueError(validation.error_message)

    # Return service functions that need state
    return {
        'validate_handle': lambda handle: validate_member_handle(state_manager, handle),
        'get_credex': lambda credex_id: get_credex(credex_id, state_manager.get("jwt_token")),
        'offer_credex': lambda data: offer_credex(data, state_manager.get("jwt_token"))
    }


def handle_login(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Handle login with strict state validation"""
    try:
        # Let StateManager validate internally
        success, result = auth_login(state_manager.get("channel")["identifier"])
        logger.info("Login attempt completed")
        return success, result

    except StateException as e:
        logger.error(f"Login error: {str(e)}")
        return False, {"message": str(e)}


def handle_registration(state_manager: Any, member_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Handle member registration with strict state validation"""
    try:
        if not isinstance(member_data, dict) or not member_data:
            raise StateException("Invalid member data")

        # Let StateManager validate internally
        success, result = auth_register(member_data, state_manager.get("channel")["identifier"])
        logger.info("Registration attempt completed")
        return success, result

    except StateException as e:
        logger.error(f"Registration error: {str(e)}")
        return False, {"message": str(e)}


def get_member_accounts(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get member accounts with strict state validation"""
    # Validate required state upfront
    validation = StateValidator.validate_before_access(
        state_manager,
        {"member_id", "jwt_token"}
    )
    if not validation.is_valid:
        return False, {"message": validation.error_message}

    try:
        member_id = state_manager.get("member_id")
        jwt_token = state_manager.get("jwt_token")

        return member_get_accounts(member_id, jwt_token)

    except Exception as e:
        logger.error(f"Failed to get member accounts: {str(e)}")
        return False, {"message": str(e)}


def get_member_dashboard(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get member dashboard with strict state validation"""
    # Validate required state upfront
    validation = StateValidator.validate_before_access(
        state_manager,
        {"channel", "jwt_token"}
    )
    if not validation.is_valid:
        return False, {"message": validation.error_message}

    try:
        channel = state_manager.get("channel")
        if not channel or "identifier" not in channel:
            raise StateException("Invalid channel data")

        jwt_token = state_manager.get("jwt_token")
        return member_get_dashboard(channel["identifier"], jwt_token)

    except StateException as e:
        error_msg = str(e)
        logger.error(f"Dashboard validation error: {error_msg}")
        return False, {"message": error_msg}


def validate_member_handle(state_manager: Any, handle: str) -> Tuple[bool, Dict[str, Any]]:
    """Validate member handle with strict state validation"""
    # Validate required state upfront
    validation = StateValidator.validate_before_access(
        state_manager,
        {"jwt_token"}
    )
    if not validation.is_valid:
        return False, {"message": validation.error_message}

    try:
        if not handle:
            raise StateException("Handle is required")

        jwt_token = state_manager.get("jwt_token")
        return member_validate_handle(handle, jwt_token)

    except StateException as e:
        error_msg = str(e)
        logger.error(f"Handle validation error: {error_msg}")
        return False, {"message": error_msg}


def refresh_member_info(state_manager: Any) -> Optional[str]:
    """Refresh member info with strict state validation"""
    # Validate required state upfront
    validation = StateValidator.validate_before_access(
        state_manager,
        {"channel"}
    )
    if not validation.is_valid:
        return validation.error_message

    try:
        channel = state_manager.get("channel")
        if not channel or "identifier" not in channel:
            raise StateException("Invalid channel data")

        return member_refresh_info(channel["identifier"])

    except StateException as e:
        error_msg = str(e)
        logger.error(f"Member refresh validation error: {error_msg}")
        return error_msg
