"""Authentication operations"""
import logging
from typing import Dict, Any, Tuple

from decouple import config
from .base import BaseAPIClient
from .profile import ProfileManager

logger = logging.getLogger(__name__)


class AuthManager(BaseAPIClient):
    """Handles authentication operations"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile_manager = ProfileManager(*args, **kwargs)

    def login(self) -> Tuple[bool, str]:
        """Handle login flow"""
        logger.info("Attempting to login")
        url = f"{self.base_url}/login"
        logger.info(f"Login URL: {url}")

        payload = {"phone": self.bot_service.user.mobile_number}
        headers = {
            "Content-Type": "application/json",
            "x-client-api-key": config("CLIENT_API_KEY"),
        }

        try:
            response = self._make_api_request(url, headers, payload)

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
                    self.profile_manager.update_profile_from_response(
                        api_response=response_data,
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
                return self._handle_error_response(
                    "Login",
                    response,
                    "Login failed: Unauthorized. Please check your credentials."
                )

            elif response.status_code == 404:
                return self._handle_error_response(
                    "Login",
                    response
                )

            else:
                return self._handle_error_response(
                    "Login",
                    response,
                    f"Login failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during login: {str(e)}")
            return False, f"Login failed: {str(e)}"

    def register_member(self, member_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Handle member registration"""
        logger.info("Attempting to register member")
        url = f"{self.base_url}/onboardMember"
        logger.info(f"Register URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, member_data)

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
                    self.profile_manager.update_profile_from_response(
                        api_response=response_data,
                        action_type="registration",
                        update_from="registration",
                        token=token
                    )

                    logger.info("Registration successful")
                    return True, "Registration successful"
                else:
                    logger.error("Registration response didn't contain a token")
                    return False, "Registration failed: No token received"

            elif response.status_code == 400:
                return self._handle_error_response(
                    "Registration",
                    response,
                    f"*Registration failed (400)*:\n\n{response.json().get('message')}"
                )

            elif response.status_code == 401:
                return self._handle_error_response(
                    "Registration",
                    response,
                    f"Registration failed: Unauthorized. {response.text}"
                )

            else:
                return self._handle_error_response(
                    "Registration",
                    response,
                    f"Registration failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during registration: {str(e)}")
            return False, f"Registration failed: {str(e)}"
