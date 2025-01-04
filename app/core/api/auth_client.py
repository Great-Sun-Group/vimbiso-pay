"""Authentication-related API operations using pure functions"""
import logging
from typing import Any, Dict, Tuple, Optional

from decouple import config

from core.utils.exceptions import SystemException
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
            elif response.status_code == 400:
                logger.info("Login failed: New user or invalid phone")
                return (
                    False,
                    {"message": "*Welcome!* \n\nIt looks like you're new here. Let's get you \nset up."}
                )
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


def register_member(payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, str]:
    """Sends a registration request to the CredEx API"""
    logger.info("Attempting to register member")
    url = f"{BASE_URL}/onboardMember"
    logger.info(f"Register URL: {url}")

    # Create headers with state manager for registration
    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
        "Authorization": f"Bearer {jwt_token}"
    }

    try:
        try:
            response = make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("data", {}).get("action", {}).get("type") == "MEMBER_REGISTERED":
                    return True, "Registration successful"
                return False, response_data.get("error", "Registration failed")
            else:
                error_response = handle_error_response(
                    "Registration",
                    response,
                    "Registration failed"
                )
                return False, error_response.get("error", {}).get("message", "Registration failed")
        except SystemException as e:
            logger.error(f"System error during registration: {str(e)}")
            return False, e.message
    except Exception as e:
        logger.exception(f"Error during registration: {str(e)}")
        return False, f"Registration failed: {str(e)}"
