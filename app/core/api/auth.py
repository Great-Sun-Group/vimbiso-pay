"""Authentication operations using pure functions"""
import logging
from typing import Dict, Any, Tuple

from decouple import config

from .base import make_api_request, get_headers, handle_error_response
from .profile import update_profile_from_response

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
                # Update profile and state
                update_profile_from_response(
                    api_response=response_data,
                    state_manager=bot_service.state_manager,
                    action_type="login",
                    update_from="login",
                    token=token
                )

                logger.info(f"Login successful {token}")
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
            return handle_error_response(
                "Login",
                response,
                "Login failed: Unauthorized. Please check your credentials."
            )

        elif response.status_code == 404:
            return handle_error_response(
                "Login",
                response
            )

        else:
            return handle_error_response(
                "Login",
                response,
                f"Login failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during login: {str(e)}")
        return False, f"Login failed: {str(e)}"


def onboard_member(bot_service: Any, member_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Handle member onboarding"""
    logger.info("Attempting to onboard member")
    url = "onboardMember"  # Relative URL - base.py will handle making it absolute
    logger.info(f"Onboard URL: {url}")

    headers = get_headers(bot_service.state_manager)
    try:
        response = make_api_request(url, headers, member_data)

        if response.status_code == 201:
            response_data = response.json()
            token = (
                response_data.get("data", {})
                .get("action", {})
                .get("details", {})
                .get("token")
            )

            if token:
                # Update profile and state
                update_profile_from_response(
                    api_response=response_data,
                    state_manager=bot_service.state_manager,
                    action_type="onboarding",
                    update_from="onboarding",
                    token=token
                )

                logger.info("Onboarding successful")
                return True, "Onboarding successful"
            else:
                logger.error("Onboarding response didn't contain a token")
                return False, "Onboarding failed: No token received"

        elif response.status_code == 400:
            return handle_error_response(
                "Onboarding",
                response,
                f"*Onboarding failed (400)*:\n\n{response.json().get('message')}"
            )

        elif response.status_code == 401:
            return handle_error_response(
                "Onboarding",
                response,
                f"Onboarding failed: Unauthorized. {response.text}"
            )

        else:
            return handle_error_response(
                "Onboarding",
                response,
                f"Onboarding failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during onboarding: {str(e)}")
        return False, f"Onboarding failed: {str(e)}"
