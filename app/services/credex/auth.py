import logging
from typing import Any, Dict, Tuple

from .base import BaseCredExService
from .config import CredExEndpoints
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class CredExAuthService(BaseCredExService):
    """Service for CredEx authentication operations"""

    def login(self, channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user with the CredEx API using channel identifier"""
        if not channel_identifier:
            raise ValidationError("Channel identifier is required")

        try:
            response = self._make_request(
                CredExEndpoints.LOGIN,
                payload={"channel_identifier": channel_identifier},
                require_auth=False
            )

            # Handle error responses according to API spec
            if response.status_code >= 400:
                try:
                    data = response.json()
                    error_data = data.get("data", {}).get("action", {})
                    error_type = error_data.get("type")
                    error_details = error_data.get("details", {})
                    error_code = error_details.get("code")
                    error_reason = error_details.get("reason", "")

                    # Handle different error types based on API spec
                    if response.status_code == 404 and error_type == "ERROR_NOT_FOUND" and error_code == "NOT_FOUND":
                        logger.info("New user detected")
                        return False, {"message": "Welcome! It looks like you're new here. Let's get you set up."}

                    if response.status_code == 400 and error_type == "ERROR_VALIDATION":
                        logger.error(f"Validation error: {error_reason}")
                        return False, {"message": error_reason or "Invalid channel identifier format"}

                    if response.status_code == 500 and error_type == "ERROR_INTERNAL":
                        logger.error(f"Server error: {error_reason}")
                        return False, {"message": "Service temporarily unavailable. Please try again later."}

                    # Handle other error cases
                    error_msg = data.get("message", "Login failed")
                    logger.error(f"Login error: {error_msg}")
                    return False, {"message": error_msg}

                except Exception as e:
                    logger.error(f"Error parsing response: {str(e)}")
                    return False, {"message": "Service error. Please try again."}

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

    def register_member(self, member_data: Dict[str, Any], channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Register a new member with channel identifier"""
        if not member_data:
            raise ValidationError("Member data is required")

        if not channel_identifier:
            raise ValidationError("Channel identifier is required")

        # Validate required fields and their formats
        required_fields = {"firstname", "lastname", "defaultDenom"}
        missing = required_fields - set(member_data.keys())
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")

        # Validate name lengths (3-50 characters)
        firstname = member_data.get("firstname", "")
        if not (3 <= len(firstname) <= 50):
            raise ValidationError("First name must be between 3 and 50 characters")

        lastname = member_data.get("lastname", "")
        if not (3 <= len(lastname) <= 50):
            raise ValidationError("Last name must be between 3 and 50 characters")

        # Add channel identifier
        member_data["channel_identifier"] = channel_identifier

        # Validate defaultDenom is valid
        valid_denoms = {"CXX", "CAD", "USD", "XAU", "ZWG"}
        if member_data.get("defaultDenom") not in valid_denoms:
            raise ValidationError(f"Invalid defaultDenom. Must be one of: {', '.join(valid_denoms)}")

        try:
            response = self._make_request(
                CredExEndpoints.REGISTER,
                payload=member_data
            )

            # Handle error responses according to API spec
            if response.status_code >= 400:
                try:
                    data = response.json()
                    error_data = data.get("data", {}).get("action", {})
                    error_type = error_data.get("type")
                    error_details = error_data.get("details", {})
                    error_code = error_details.get("code")
                    error_reason = error_details.get("reason", "")

                    # Handle specific error types based on API spec
                    if response.status_code == 409:
                        if error_code == "DUPLICATE_PHONE":
                            logger.error(f"Channel identifier already in use: {error_reason}")
                            return False, {"message": "This identifier is already registered"}
                        return False, {"message": data.get("message", "Registration failed: Duplicate data")}

                    if error_type == "ERROR_VALIDATION":
                        if error_code == "MISSING_PARAMS":
                            logger.error(f"Missing parameters: {error_reason}")
                            return False, {"message": error_reason or "Please provide all required information"}
                        logger.error(f"Validation error: {error_reason}")
                        return False, {"message": error_reason or "Please check your information and try again"}

                    if error_type == "ERROR_INTERNAL":
                        logger.error(f"Server error during registration: {error_reason}")
                        suggestion = error_details.get("suggestion", "Please try again later")
                        return False, {"message": f"Service temporarily unavailable. {suggestion}"}

                    # Handle other error cases
                    error_msg = data.get("message", "Registration failed")
                    logger.error(f"Registration error: {error_msg}")
                    return False, {"message": error_msg}

                except Exception as e:
                    logger.error(f"Error parsing registration response: {str(e)}")
                    return False, {"message": "Service error. Please try again."}

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

    def refresh_token(self, channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Refresh authentication token using channel identifier"""
        try:
            response = self._make_request(
                CredExEndpoints.LOGIN,
                payload={"channel_identifier": channel_identifier},
                require_auth=False
            )

            # Handle error responses according to API spec
            if response.status_code >= 400:
                try:
                    data = response.json()
                    error_data = data.get("data", {}).get("action", {})
                    error_type = error_data.get("type")
                    error_details = error_data.get("details", {})
                    error_code = error_details.get("code")
                    error_reason = error_details.get("reason", "")

                    # Handle different error types based on API spec
                    if response.status_code == 404 and error_type == "ERROR_NOT_FOUND" and error_code == "NOT_FOUND":
                        logger.info("Member not found during token refresh")
                        return False, {"message": "Session expired. Please try again."}

                    if response.status_code == 400 and error_type == "ERROR_VALIDATION":
                        logger.error(f"Validation error during refresh: {error_reason}")
                        return False, {"message": error_reason or "Invalid channel identifier format"}

                    if response.status_code == 500 and error_type == "ERROR_INTERNAL":
                        logger.error(f"Server error during refresh: {error_reason}")
                        return False, {"message": "Service temporarily unavailable. Please try again later."}

                    # Handle other error cases
                    error_msg = data.get("message", "Token refresh failed")
                    logger.error(f"Refresh error: {error_msg}")
                    return False, {"message": error_msg}

                except Exception as e:
                    logger.error(f"Error parsing refresh response: {str(e)}")
                    return False, {"message": "Service error. Please try again."}

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
