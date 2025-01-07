"""Authentication operations using pure functions"""
import logging
from typing import Dict, Any, Tuple

from decouple import config

from .base import make_api_request, handle_api_response

logger = logging.getLogger(__name__)


def login(bot_service: Any) -> Tuple[bool, str]:
    """Handle login flow"""
    logger.info("Attempting to login")
    url = "login"  # Relative URL - base.py will handle making it absolute
    logger.info(f"Login URL: {url}")

    # Get channel info from state manager
    channel = bot_service.state_manager.get("channel")
    if not channel or not channel.get("identifier"):
        logger.error("No channel identifier found")
        return False, "Login failed: No channel identifier"

    payload = {"phone": channel["identifier"]}
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
                # Handle response through dashboard handler
                response_data, error = handle_api_response(
                    response=response,
                    state_manager=bot_service.state_manager,
                    auth_token=token
                )
                if error:
                    return False, error

                logger.info("Login successful")
                return True, "Login successful"
            else:
                logger.error("Login response didn't contain a token")
                return False, "Login failed: No token received"

        elif response.status_code == 400:
            logger.info("Login failed: New user or invalid phone")
            return (
                False,
                "*Welcome!* \n\nIt looks like you're new here. Let's get you \nset up.",
            )

        elif response.status_code == 401:
            return False, "Login failed: Unauthorized. Please check your credentials."

        elif response.status_code == 404:
            return False, "Login failed: Resource not found"

        else:
            return False, f"Login failed: Unexpected error (status code: {response.status_code})"

    except Exception as e:
        logger.exception(f"Error during login: {str(e)}")
        return False, f"Login failed: {str(e)}"


def onboard_member(bot_service: Any, member_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Handle member onboarding

    Args:
        bot_service: Bot service instance with state manager
        member_data: Dictionary containing member registration data
            Required fields:
            - firstname: Member's first name
            - lastname: Member's last name
            - phone: Member's phone number
            - defaultDenom: Default denomination for member (e.g. "USD")

    Returns:
        Tuple[bool, Dict[str, Any]]: Success flag and either:
            - On success: Dict with response data
            - On failure: Dict with "message" error string
    """
    logger.info("Attempting to onboard member")
    url = "onboardMember"  # Relative URL - base.py will handle making it absolute
    logger.info(f"Onboard URL: {url}")

    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
    }

    try:
        response = make_api_request(url, headers, member_data)

        if response.status_code == 201:
            response_data = response.json()
            details = (
                response_data.get("data", {})
                .get("action", {})
                .get("details", {})
            )

            token = details.get("token")
            if not token:
                logger.error("Onboarding response missing token")
                return False, {"message": "Onboarding failed: Invalid response data"}

            # Handle response through dashboard handler
            response_data, error = handle_api_response(
                response=response,
                state_manager=bot_service.state_manager,
                auth_token=token
            )
            if error:
                return False, {"message": error}

            logger.info("Onboarding successful")
            return True, response_data

        else:
            error_msg = f"Onboarding failed: Unexpected error (status code: {response.status_code})"
            logger.error(error_msg)
            return False, {"message": error_msg}

    except Exception as e:
        logger.exception(f"Error during onboarding: {str(e)}")
        return False, {"message": f"Onboarding failed: {str(e)}"}
