"""Dashboard and member operations using pure functions"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException

from .auth import login
from .base import (BASE_URL, get_headers,
                   handle_reset_and_init, make_api_request,
                   process_api_response)
from .profile import (_structure_profile_data, handle_successful_refresh,
                      update_profile_from_response)

logger = logging.getLogger(__name__)


def _process_dashboard_response(
    state_manager: Any,
    response_data: Dict[str, Any],
    action_type: str = "dashboard_fetch"
) -> Tuple[bool, Dict[str, Any]]:
    """Process dashboard API response through state validation"""
    try:
        # Structure profile data through state validation
        profile_data = _structure_profile_data(
            response_data,
            state_manager,
            action_type
        )

        if not profile_data:
            raise StateException("Failed to structure profile data")

        # Return validated response
        return True, {
            "data": {
                "dashboard": profile_data["dashboard"],
                "action": profile_data["action"]
            }
        }

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "process_dashboard_response",
                "action_type": action_type
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        return False, {"message": str(e)}


def get_dashboard(bot_service: Any) -> Tuple[bool, Dict[str, Any]]:
    """Fetch member's dashboard through state validation"""
    logger.info("Fetching member dashboard")

    try:
        # Get channel ID through state validation
        channel = bot_service.user.state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Invalid channel state")

        url = f"{BASE_URL}/getMemberDashboardByPhone"
        payload = {"phone": channel["identifier"]}
        headers = get_headers(bot_service.user.state_manager)

        # Make initial request
        response = make_api_request(url, headers, payload, retry_auth=False)
        if response.status_code == 200:
            return _process_dashboard_response(
                bot_service.user.state_manager,
                response.json()
            )

        # Handle unauthorized - try refresh and retry
        if response.status_code == 401:
            success, _ = login(BASE_URL, bot_service)
            if success:
                response = make_api_request(url, headers, payload)
                if response.status_code == 200:
                    return _process_dashboard_response(
                        bot_service.user.state_manager,
                        response.json()
                    )

        # Handle other errors
        error_context = ErrorContext(
            error_type="api",
            message=f"Dashboard fetch failed (status: {response.status_code})",
            details={"status_code": response.status_code}
        )
        return False, ErrorHandler.create_error_response(error_context)

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",
            message=str(e),
            details={"operation": "get_dashboard"}
        )
        ErrorHandler.handle_error(e, bot_service.user.state_manager, error_context)
        return False, {"message": str(e)}


def refresh_member_info(
    bot_service: Any,
    reset: bool = True,
    silent: bool = True,
    init: bool = False
) -> Optional[str]:
    """Refresh member information through state validation"""
    logger.info("Refreshing member info")

    try:
        # Handle initialization
        handle_reset_and_init(
            bot_service.user.state_manager,
            bot_service,
            reset,
            silent,
            init
        )

        # Get channel ID through state validation
        channel = bot_service.user.state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Invalid channel state")

        # Make API request
        url = f"{BASE_URL}/getMemberDashboardByPhone"
        payload = {"phone": channel["identifier"]}
        headers = get_headers(bot_service.user.state_manager)

        response = make_api_request(url, headers, payload)
        response_data = process_api_response(response)

        # Handle API errors
        error_messages = [
            "Member not found",
            "Could not retrieve member dashboard",
            "Invalid token"
        ]
        if any(msg in response_data.get("message", "") for msg in error_messages):
            error_context = ErrorContext(
                error_type="api",
                message="Member not found or invalid token",
                details={"response": response_data}
            )
            return ErrorHandler.create_error_response(error_context)["data"]["action"]["details"]["message"]

        # Handle successful refresh through state validation
        return handle_successful_refresh(
            response_data,
            bot_service.user.state_manager
        )

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",
            message=str(e),
            details={"operation": "refresh_member_info"}
        )
        ErrorHandler.handle_error(e, bot_service.user.state_manager, error_context)
        return str(e)


def validate_account_handle(bot_service: Any, handle: str) -> Tuple[bool, Dict[str, Any]]:
    """Validate member handle through state validation"""
    logger.info(f"Validating handle: {handle}")

    try:
        url = f"{BASE_URL}/getAccountByHandle"
        payload = {"accountHandle": handle.lower()}
        headers = get_headers(bot_service.user.state_manager)

        response = make_api_request(url, headers, payload, method="POST")
        if response.status_code == 200:
            response_data = response.json()
            if not response_data.get("Error"):
                logger.info("Handle validation successful")
                return True, response_data

            error_context = ErrorContext(
                error_type="input",
                message="Handle validation failed",
                details={"handle": handle}
            )
            return False, ErrorHandler.create_error_response(error_context)

        error_context = ErrorContext(
            error_type="api",
            message=f"Handle validation failed (status: {response.status_code})",
            details={"status_code": response.status_code}
        )
        return False, ErrorHandler.create_error_response(error_context)

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",
            message=str(e),
            details={
                "operation": "validate_handle",
                "handle": handle
            }
        )
        ErrorHandler.handle_error(e, bot_service.user.state_manager, error_context)
        return False, {"error": str(e)}


def get_ledger(bot_service: Any, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Get member's transaction ledger through state validation"""
    logger.info("Fetching ledger")

    try:
        url = f"{BASE_URL}/getLedger"
        headers = get_headers(bot_service.user.state_manager)

        response = make_api_request(url, headers, payload)
        if response.status_code == 200:
            response_data = response.json()

            # Update profile through state validation
            update_profile_from_response(
                response_data,
                bot_service.user.state_manager,
                "ledger_fetch",
                "ledger_fetch"
            )

            logger.info("Ledger fetched successfully")
            return True, response_data

        error_context = ErrorContext(
            error_type="api",
            message=f"Ledger fetch failed (status: {response.status_code})",
            details={"status_code": response.status_code}
        )
        return False, ErrorHandler.create_error_response(error_context)

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",
            message=str(e),
            details={"operation": "get_ledger"}
        )
        ErrorHandler.handle_error(e, bot_service.user.state_manager, error_context)
        return False, {"error": str(e)}
