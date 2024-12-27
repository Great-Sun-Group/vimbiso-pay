"""CredEx service using pure functions with strict state validation"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.state_validator import StateValidator
from core.utils.exceptions import StateException

from .auth import login as auth_login, register_member as auth_register
from .member import (
    get_dashboard as member_get_dashboard,
    validate_handle as member_validate_handle,
    refresh_member_info as member_refresh_info,
    get_member_accounts as member_get_accounts,
)

logger = logging.getLogger(__name__)


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
