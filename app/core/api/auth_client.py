import logging
from typing import Tuple, Dict, Any
from .base_client import BaseAPIClient

logger = logging.getLogger(__name__)


class AuthClient(BaseAPIClient):
    """Handles authentication-related API operations"""

    def login(self, phone_number: str) -> Tuple[bool, str]:
        """Sends a login request to the CredEx API"""
        logger.info("Attempting to login")
        url = f"{self.base_url}/login"
        logger.info(f"Login URL: {url}")

        payload = {"phone": phone_number}
        headers = self._get_headers()

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
                logger.error(f"Login failed with status code: {response.status_code}")
                return False, f"Login failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during login: {str(e)}")
            return False, f"Login failed: {str(e)}"

    def register_member(self, payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, str]:
        """Sends a registration request to the CredEx API"""
        logger.info("Attempting to register member")
        url = f"{self.base_url}/onboardMember"
        logger.info(f"Register URL: {url}")

        headers = self._get_headers(jwt_token)
        try:
            response = self._make_api_request(url, headers, payload)
            success, response_data = self._handle_response(response, "MEMBER_REGISTERED")
            if success:
                return True, "Registration successful"
            return False, response_data.get("error", "Registration failed")
        except Exception as e:
            logger.exception(f"Error during registration: {str(e)}")
            return False, f"Registration failed: {str(e)}"
