"""Authentication-related API operations using pure functions"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import SystemException
from decouple import config

from .base import BASE_URL, handle_error_response, make_api_request

logger = logging.getLogger(__name__)


# Store last login response for state updates
_last_login_response = None


def login(phone_number: str) -> Tuple[bool, Dict[str, Any]]:
    """Sends a login request to the CredEx API

    Returns:
        Tuple[bool, Dict[str, Any]]: Success flag and either response data or error message
    """
    global _last_login_response
    logger.info("Attempting to login")
    url = f"{BASE_URL}/login"
    logger.info(f"Login URL: {url}")

    payload = {"phone": phone_number}
    # Use get_headers without state_manager for login
    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
    }

    try:
        try:
            response = make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get("data", {})
                details = data.get("action", {}).get("details", {})
                if details.get("token") and details.get("memberID"):
                    logger.info("Login successful")
                    # Store full response for state manager to inject properly into state
                    _last_login_response = response_data
                    # Return success with auth details only - dashboard goes through state
                    return True, {
                        "token": details["token"],
                        "memberID": details["memberID"]
                    }
                else:
                    logger.error("Login response missing required fields")
                    return False, "Login failed: Invalid response data"
            elif response.status_code in [400, 404]:
                # Both 400 and 404 indicate a new user
                logger.info("Login failed: New user")
                return False, {}
            else:
                error_response = handle_error_response(
                    "Login",
                    response,
                    f"Login failed: Unexpected error (status code: {response.status_code})"
                )
                return False, {"message": error_response.get("error", {}).get("message", "Login failed")}
        except SystemException as e:
            logger.error(f"System error during login: {str(e)}")
            return False, {"message": e.message}
    except Exception as e:
        logger.exception(f"Error during login: {str(e)}")
        return False, {"message": f"Login failed: {str(e)}"}


def get_login_response_data() -> Optional[Dict[str, Any]]:
    """Get last login response data for state updates"""
    return _last_login_response


# Store last onboarding response for state updates
_last_onboarding_response = None


def onboard_member(member_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Sends an onboarding request to the CredEx API

    Args:
        member_data: Dictionary containing member registration data
            Required fields:
            - firstname: Member's first name
            - lastname: Member's last name
            - phone: Member's phone number
            - defaultDenom: Default denomination for member (e.g. "USD")

    Returns:
        Tuple[bool, Dict[str, Any]]: Success flag and either:
            - On success: Dict with "token" and "memberID"
            - On failure: Dict with "message" error string
    """
    global _last_onboarding_response
    logger.info("Attempting to onboard member")
    url = f"{BASE_URL}/onboardMember"
    logger.info(f"Onboard URL: {url}")

    # Use get_headers without state_manager for onboarding
    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
    }

    try:
        try:
            response = make_api_request(url, headers, member_data)
            if response.status_code == 201:  # Onboarding creates new member
                response_data = response.json()
                data = response_data.get("data", {})
                details = data.get("action", {}).get("details", {})
                if details.get("token") and details.get("memberID"):
                    logger.info("Onboarding successful")
                    # Store full response for state manager to inject properly into state
                    _last_onboarding_response = response_data
                    # Return success with auth details only - dashboard goes through state
                    return True, {
                        "token": details["token"],
                        "memberID": details["memberID"]
                    }
                else:
                    logger.error("Onboarding response missing required fields")
                    return False, {"message": "Onboarding failed: Invalid response data"}
            else:
                error_response = handle_error_response(
                    "Onboarding",
                    response,
                    f"Onboarding failed: Unexpected error (status code: {response.status_code})"
                )
                return False, {"message": error_response.get("error", {}).get("message", "Onboarding failed")}
        except SystemException as e:
            logger.error(f"System error during onboarding: {str(e)}")
            return False, {"message": e.message}
    except Exception as e:
        logger.exception(f"Error during onboarding: {str(e)}")
        return False, {"message": f"Onboarding failed: {str(e)}"}


def get_onboarding_response_data() -> Optional[Dict[str, Any]]:
    """Get last onboarding response data for state updates"""
    return _last_onboarding_response
