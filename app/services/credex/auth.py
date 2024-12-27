import logging
from typing import Any, Dict, Optional, Tuple

from .base import BaseCredExService
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class CredExAuthService(BaseCredExService):
    """CredEx authentication service with simplified error handling"""

    def _validate_member_data(self, member_data: Dict[str, Any]) -> None:
        """Validate member registration data enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input type
            if not isinstance(member_data, dict):
                raise ValidationError("Member data must be a dictionary")
            if not member_data:
                raise ValidationError("Member data is required")

            # Check required fields
            required_fields = {"firstname", "lastname", "defaultDenom"}
            if missing := required_fields - set(member_data.keys()):
                raise ValidationError(f"Missing required fields: {', '.join(missing)}")

            # Validate field types
            for field in ["firstname", "lastname"]:
                if not isinstance(member_data[field], str):
                    raise ValidationError(f"{field.title()} must be a string")

            # Validate name lengths
            for field in ["firstname", "lastname"]:
                length = len(member_data[field].strip())
                if not (3 <= length <= 50):
                    raise ValidationError(f"{field.title()} must be between 3 and 50 characters")

            # Validate denomination
            valid_denoms = {"CXX", "CAD", "USD", "XAU", "ZWG"}
            denom = member_data.get("defaultDenom")
            if not isinstance(denom, str):
                raise ValidationError("Denomination must be a string")
            if denom not in valid_denoms:
                raise ValidationError(f"Invalid defaultDenom. Must be one of: {', '.join(valid_denoms)}")

            logger.info("Member data validation successful")

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Member data validation error: {str(e)}")
            raise ValidationError(f"Invalid member data: {str(e)}")

    def _extract_token(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract token from response data enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not isinstance(data, dict):
                raise ValueError("Response data must be a dictionary")
            if not data:
                raise ValueError("Response data is empty")

            # Extract token using safe navigation
            token = (data.get("data", {})
                     .get("action", {})
                     .get("details", {})
                     .get("token"))

            if token and not isinstance(token, str):
                raise ValueError("Invalid token format")

            return token

        except Exception as e:
            logger.error(f"Token extraction error: {str(e)}")
            return None

    def login(self, channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not isinstance(channel_identifier, str):
                raise ValidationError("Channel identifier must be a string")
            if not channel_identifier.strip():
                raise ValidationError("Channel identifier is required")

            # Log login attempt
            logger.info(f"Attempting login for channel {channel_identifier}")

            # Make API request
            response = self._make_request(
                'auth', 'login',
                payload={"phone": channel_identifier}  # Map to phone for API compatibility
            )

            # Parse and validate response
            if not response.ok:
                error_msg = f"Login request failed: {response.status_code}"
                logger.error(f"{error_msg} for channel {channel_identifier}")
                return False, {"message": error_msg}

            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"Invalid response format: {str(e)}"
                logger.error(f"{error_msg} for channel {channel_identifier}")
                return False, {"message": error_msg}

            # Extract and validate token
            if token := self._extract_token(data):
                self._update_token(token)
                logger.info(f"Login successful for channel {channel_identifier}")
                return True, data

            error_msg = "Login failed: No token received"
            logger.error(f"{error_msg} for channel {channel_identifier}")
            return False, {"message": error_msg}

        except ValidationError as e:
            logger.error(f"Login validation error: {str(e)} for channel {channel_identifier}")
            return False, {"message": str(e)}
        except Exception as e:
            logger.error(f"Login error: {str(e)} for channel {channel_identifier}")
            return False, {"message": "Login failed due to system error"}

    def register_member(self, member_data: Dict[str, Any], channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Register new member enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate inputs
            if not isinstance(channel_identifier, str):
                raise ValidationError("Channel identifier must be a string")
            if not channel_identifier.strip():
                raise ValidationError("Channel identifier is required")

            # Validate member data
            self._validate_member_data(member_data)

            # Log registration attempt
            logger.info(f"Attempting registration for channel {channel_identifier}")

            # Make API request
            response = self._make_request('auth', 'register', payload=member_data)

            # Parse and validate response
            if not response.ok:
                error_msg = f"Registration request failed: {response.status_code}"
                logger.error(f"{error_msg} for channel {channel_identifier}")
                return False, {"message": error_msg}

            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"Invalid response format: {str(e)}"
                logger.error(f"{error_msg} for channel {channel_identifier}")
                return False, {"message": error_msg}

            # Extract and validate token
            if token := self._extract_token(data):
                self._update_token(token)
                logger.info(f"Registration successful for channel {channel_identifier}")
                return True, data

            error_msg = "Registration failed: No token received"
            logger.error(f"{error_msg} for channel {channel_identifier}")
            return False, {"message": error_msg}

        except ValidationError as e:
            logger.error(f"Registration validation error: {str(e)} for channel {channel_identifier}")
            return False, {"message": str(e)}
        except Exception as e:
            logger.error(f"Registration error: {str(e)} for channel {channel_identifier}")
            return False, {"message": "Registration failed due to system error"}

    def refresh_token(self, channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Refresh authentication token enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not isinstance(channel_identifier, str):
                raise ValidationError("Channel identifier must be a string")
            if not channel_identifier.strip():
                raise ValidationError("Channel identifier is required")

            # Log refresh attempt
            logger.info(f"Attempting token refresh for channel {channel_identifier}")

            # Make API request
            response = self._make_request(
                'auth', 'login',
                payload={"phone": channel_identifier}  # Map to phone for API compatibility
            )

            # Parse and validate response
            if not response.ok:
                error_msg = f"Token refresh request failed: {response.status_code}"
                logger.error(f"{error_msg} for channel {channel_identifier}")
                return False, {"message": error_msg}

            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"Invalid response format: {str(e)}"
                logger.error(f"{error_msg} for channel {channel_identifier}")
                return False, {"message": error_msg}

            # Extract and validate token
            if token := self._extract_token(data):
                self._update_token(token)
                logger.info(f"Token refresh successful for channel {channel_identifier}")
                return True, data

            error_msg = "Token refresh failed: No token received"
            logger.error(f"{error_msg} for channel {channel_identifier}")
            return False, {"message": error_msg}

        except ValidationError as e:
            logger.error(f"Token refresh validation error: {str(e)} for channel {channel_identifier}")
            return False, {"message": str(e)}
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)} for channel {channel_identifier}")
            return False, {"message": "Token refresh failed due to system error"}
