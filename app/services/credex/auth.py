import logging
from typing import Any, Dict, Tuple

from .base import BaseCredExService
from .config import CredExEndpoints
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class CredExAuthService(BaseCredExService):
    """Service for CredEx authentication operations"""

    def login(self, phone: str) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user with the CredEx API"""
        if not phone:
            raise ValidationError("Phone number is required")

        try:
            response = self._make_request(
                CredExEndpoints.LOGIN,
                payload={"phone": phone},
                require_auth=False
            )

            # Handle error responses
            if response.status_code >= 400:
                # Check response data for member not found cases
                try:
                    data = response.json()
                    if (data.get("message") == "Member not found" or
                            data.get("data", {}).get("action", {}).get("details", {}).get("reason") == "Member not found"):
                        logger.info("New user detected")
                        return False, {"message": "Welcome! It looks like you're new here. Let's get you set up."}
                except Exception:
                    pass

                # Handle other 400 cases as new users
                if response.status_code == 400:
                    logger.info("New user detected")
                    return False, {"message": "Welcome! It looks like you're new here. Let's get you set up."}

                error_result = self._handle_error_response(response, {
                    400: "Invalid phone number or new user",
                    401: "Authentication failed"
                })
                return error_result

            data = response.json()
            token = (
                data.get("data", {})
                .get("action", {})
                .get("details", {})
                .get("token")
            )
            if token:
                # Set token and propagate to parent service if available
                self._jwt_token = token
                if hasattr(self, '_parent_service'):
                    self._parent_service.jwt_token = token
                logger.info("Login successful")
                return True, data
            else:
                logger.error("Login response didn't contain a token")
                return False, {"message": "Login failed: No token received"}

        except Exception as e:
            logger.exception(f"Login failed: {str(e)}")
            return False, {"message": f"Login failed: {str(e)}"}

    def register_member(self, member_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Register a new member"""
        if not member_data:
            raise ValidationError("Member data is required")

        try:
            response = self._make_request(
                CredExEndpoints.REGISTER,
                payload=member_data
            )

            # Handle error responses
            if response.status_code >= 400:
                error_result = self._handle_error_response(response, {
                    400: "Invalid registration data",
                    401: "Unauthorized registration attempt"
                })
                return error_result

            data = response.json()
            if response.status_code == 201:
                token = (
                    data.get("data", {})
                    .get("action", {})
                    .get("details", {})
                    .get("token")
                )
                if token:
                    # Set token and propagate to parent service if available
                    self._jwt_token = token
                    if hasattr(self, '_parent_service'):
                        self._parent_service.jwt_token = token
                    logger.info("Registration successful")
                    return True, data
                else:
                    logger.error("Registration response didn't contain a token")
                    return False, {"message": "Registration failed: No token received"}
            else:
                error_msg = data.get("message", "Registration failed")
                logger.error(f"Registration failed: {error_msg}")
                return False, {"message": error_msg}

        except Exception as e:
            logger.exception(f"Registration failed: {str(e)}")
            return False, {"message": f"Registration failed: {str(e)}"}

    def refresh_token(self, phone: str) -> Tuple[bool, Dict[str, Any]]:
        """Refresh authentication token"""
        try:
            response = self._make_request(
                CredExEndpoints.LOGIN,
                payload={"phone": phone},
                require_auth=False
            )

            # Handle error responses
            if response.status_code >= 400:
                error_result = self._handle_error_response(response, {
                    400: "Invalid phone number",
                    401: "Authentication failed"
                })
                return error_result

            data = response.json()
            token = (
                data.get("data", {})
                .get("action", {})
                .get("details", {})
                .get("token")
            )
            if token:
                # Set token and propagate to parent service if available
                self._jwt_token = token
                if hasattr(self, '_parent_service'):
                    self._parent_service.jwt_token = token
                logger.info("Token refresh successful")
                return True, data
            else:
                logger.error("Token refresh response didn't contain a token")
                return False, {"message": "Token refresh failed: No token received"}

        except Exception as e:
            logger.exception(f"Token refresh failed: {str(e)}")
            return False, {"message": f"Token refresh failed: {str(e)}"}
