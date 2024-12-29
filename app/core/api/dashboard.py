"""Dashboard and member operations using pure functions"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.state_validator import StateValidator

from .auth import login
from .base import (BASE_URL, get_headers, handle_error_response,
                   handle_reset_and_init, make_api_request,
                   process_api_response)
from .profile import (_structure_profile_data, handle_successful_refresh,
                      update_profile_from_response)

logger = logging.getLogger(__name__)


def get_dashboard(bot_service: Any) -> Tuple[bool, Dict[str, Any]]:
    """Fetch member's dashboard"""
    logger.info("Fetching member dashboard")
    url = f"{BASE_URL}/getMemberDashboardByPhone"
    logger.info(f"Dashboard URL: {url}")

    channel_identifier = bot_service.user.state_manager.get("channel", {}).get("identifier")
    payload = {"phone": channel_identifier}
    headers = get_headers(bot_service.user.state_manager)

    try:
        response = make_api_request(url, headers, payload, retry_auth=False)
        if response.status_code == 200:
            response_data = response.json()
            # Get required state fields with validation at boundary
            required_fields = {"profile", "current_account", "jwt_token", "authenticated"}
            current_state = {
                field: bot_service.user.state_manager.get(field)
                for field in required_fields
            }

            # Validate at boundary
            validation = StateValidator.validate_state(current_state)
            if not validation.is_valid:
                logger.error(f"Invalid state: {validation.error_message}")
                return False, {"message": "Invalid state"}

            # Add current state's action data to response to preserve it
            if "data" not in response_data:
                response_data["data"] = {}
            if "action" not in response_data["data"]:
                response_data["data"]["action"] = {}

            # Preserve existing action data
            current_action = current_state.get("profile", {}).get("action", {})
            response_data["data"]["action"].update({
                "message": current_action.get("message", ""),
                "status": current_action.get("status", ""),
                "type": current_action.get("type", "dashboard_fetch")
            })

            # Structure profile data from dashboard response
            profile_data = _structure_profile_data(
                response_data,
                bot_service.user.state_manager,
                "dashboard_fetch"
            )

            logger.info("Dashboard fetched successfully")
            return True, {
                "data": {
                    "dashboard": profile_data["dashboard"],
                    "action": profile_data["action"]
                }
            }

        elif response.status_code == 401:
            # Try to refresh token and retry
            success, _ = login(BASE_URL, bot_service)
            if success:
                response = make_api_request(url, headers, payload)
                if response.status_code == 200:
                    response_data = response.json()
                    # Get required state fields with validation at boundary
                    required_fields = {"profile", "current_account", "jwt_token", "authenticated"}
                    current_state = {
                        field: bot_service.user.state_manager.get(field)
                        for field in required_fields
                    }

                    # Validate at boundary
                    validation = StateValidator.validate_state(current_state)
                    if not validation.is_valid:
                        logger.error(f"Invalid state: {validation.error_message}")
                        return False, {"message": "Invalid state"}

                    # Add current state's action data to response to preserve it
                    if "data" not in response_data:
                        response_data["data"] = {}
                    if "action" not in response_data["data"]:
                        response_data["data"]["action"] = {}

                    # Preserve existing action data
                    current_action = current_state.get("profile", {}).get("action", {})
                    response_data["data"]["action"].update({
                        "message": current_action.get("message", ""),
                        "status": current_action.get("status", ""),
                        "type": current_action.get("type", "dashboard_fetch")
                    })

                    # Structure profile data from dashboard response
                    profile_data = _structure_profile_data(
                        response_data,
                        bot_service.user.state_manager,
                        "dashboard_fetch"
                    )

                    logger.info("Dashboard fetched successfully after reauth")
                    return True, {
                        "data": {
                            "dashboard": profile_data["dashboard"],
                            "action": profile_data["action"]
                        }
                    }

            return handle_error_response(
                "Dashboard fetch",
                response,
                "Dashboard fetch failed: Unauthorized"
            )

        else:
            return handle_error_response(
                "Dashboard fetch",
                response,
                f"Dashboard fetch failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during dashboard fetch: {str(e)}")
        return False, {"message": f"Dashboard fetch failed: {str(e)}"}


def refresh_member_info(
    bot_service: Any,
    reset: bool = True,
    silent: bool = True,
    init: bool = False
) -> Optional[str]:
    """Refresh member information"""
    logger.info("Refreshing member info")

    # Get required state fields with validation at boundary
    required_fields = {"profile", "current_account", "jwt_token", "authenticated"}
    current_state = {
        field: bot_service.user.state_manager.get(field)
        for field in required_fields
    }

    # Validate at boundary
    validation = StateValidator.validate_state(current_state)
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return "Invalid state"

    # Handle initialization messages
    handle_reset_and_init(bot_service.user.state_manager, bot_service, reset, silent, init)

    try:
        url = f"{BASE_URL}/getMemberDashboardByPhone"
        channel_identifier = bot_service.user.state_manager.get("channel", {}).get("identifier")
        payload = {"phone": channel_identifier}
        headers = get_headers(bot_service.user.state_manager)

        response = make_api_request(url, headers, payload)
        response_data = process_api_response(response)

        if (
            "Member not found" in response_data.get("message", "")
            or "Could not retrieve member dashboard" in response_data.get("message", "")
            or "Invalid token" in response_data.get("message", "")
        ):
            return "Member not found or invalid token"

        # Handle successful refresh
        return handle_successful_refresh(
            response_data,
            bot_service.user.state_manager
        )

    except Exception as e:
        logger.exception(f"Error during refresh: {str(e)}")
        return str(e)


def validate_account_handle(bot_service: Any, handle: str) -> Tuple[bool, Dict[str, Any]]:
    """Validate member handle"""
    logger.info(f"Validating handle: {handle}")
    url = f"{BASE_URL}/getAccountByHandle"
    logger.info(f"Handle validation URL: {url}")

    payload = {"accountHandle": handle.lower()}
    headers = get_headers(bot_service.user.state_manager)

    try:
        response = make_api_request(url, headers, payload, method="POST")
        if response.status_code == 200:
            response_data = response.json()
            if not response_data.get("Error"):
                logger.info("Handle validation successful")
                return True, response_data
            else:
                logger.error("Handle validation failed")
                return False, response_data
        else:
            return handle_error_response(
                "Handle validation",
                response,
                f"Handle validation failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during handle validation: {str(e)}")
        return False, {"error": f"Handle validation failed: {str(e)}"}


def get_ledger(bot_service: Any, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Get member's transaction ledger"""
    logger.info("Fetching ledger")
    url = f"{BASE_URL}/getLedger"
    logger.info(f"Ledger URL: {url}")

    headers = get_headers(bot_service.user.state_manager)
    try:
        response = make_api_request(url, headers, payload)
        if response.status_code == 200:
            response_data = response.json()
            # Structure profile data from get ledger response
            update_profile_from_response(
                response_data,
                bot_service.user.state_manager,
                "ledger_fetch",
                "ledger_fetch"
            )
            logger.info("Ledger fetched successfully")
            return True, response_data

        else:
            return handle_error_response(
                "Ledger fetch",
                response,
                f"Ledger fetch failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during ledger fetch: {str(e)}")
        return False, {"error": f"Ledger fetch failed: {str(e)}"}
