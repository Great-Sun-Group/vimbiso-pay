"""Authentication-related API operations using pure functions"""
import logging
from typing import Tuple, Dict, Any
from decouple import config
from .base import (
    make_api_request,
    handle_error_response,
    BASE_URL
)

logger = logging.getLogger(__name__)


def login(phone_number: str) -> Tuple[bool, str]:
    """Sends a login request to the CredEx API"""
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
        response = make_api_request(url, headers, payload)
        if response.status_code == 200:
            response_data = response.json()
            token = (
                response_data.get("data", {})
                .get("action", {})
                .get("details", {})
                .get("token")
            )
            if token:
                logger.info("Login successful")
                return True, token
            else:
                logger.error("Login response didn't contain a token")
                return False, "Login failed: No token received"
        elif response.status_code == 400:
            logger.info("Login failed: New user or invalid phone")
            return (
                False,
                "*Welcome!* \n\nIt looks like you're new here. Let's get you \nset up.",
            )
        else:
            success, error_msg = handle_error_response(
                "Login",
                response,
                f"Login failed: Unexpected error (status code: {response.status_code})"
            )
            return False, error_msg
    except Exception as e:
        logger.exception(f"Error during login: {str(e)}")
        return False, f"Login failed: {str(e)}"


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
        response = make_api_request(url, headers, payload)
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("data", {}).get("action", {}).get("type") == "MEMBER_REGISTERED":
                return True, "Registration successful"
            return False, response_data.get("error", "Registration failed")
        else:
            success, error_msg = handle_error_response(
                "Registration",
                response,
                "Registration failed"
            )
            return False, error_msg
    except Exception as e:
        logger.exception(f"Error during registration: {str(e)}")
        return False, f"Registration failed: {str(e)}"
