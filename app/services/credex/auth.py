import logging
from typing import Any, Dict, Optional, Tuple

from .base import BaseCredExService
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class CredExAuthService(BaseCredExService):
    """CredEx authentication service with simplified error handling"""

    def _validate_member_data(self, member_data: Dict[str, Any]) -> None:
        """Validate member registration data"""
        if not member_data:
            raise ValidationError("Member data is required")

        # Check required fields
        required_fields = {"firstname", "lastname", "defaultDenom"}
        if missing := required_fields - set(member_data.keys()):
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")

        # Validate name lengths
        for field in ["firstname", "lastname"]:
            if not (3 <= len(member_data[field]) <= 50):
                raise ValidationError(f"{field.title()} must be between 3 and 50 characters")

        # Validate denomination
        valid_denoms = {"CXX", "CAD", "USD", "XAU", "ZWG"}
        if member_data["defaultDenom"] not in valid_denoms:
            raise ValidationError(f"Invalid defaultDenom. Must be one of: {', '.join(valid_denoms)}")

    def _extract_token(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract token from response data"""
        return (data.get("data", {})
                .get("action", {})
                .get("details", {})
                .get("token"))

    def login(self, channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user with channel identifier"""
        if not channel_identifier:
            raise ValidationError("Channel identifier is required")

        try:
            response = self._make_request(
                'auth', 'login',
                payload={"phone": channel_identifier}  # Map to phone for API compatibility
            )
            data = response.json()

            if token := self._extract_token(data):
                self._update_token(token)
                logger.info("Login successful")
                return True, data
            return False, {"message": "Login failed: No token received"}

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False, {"message": str(e)}

    def register_member(self, member_data: Dict[str, Any], channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Register new member"""
        if not channel_identifier:
            raise ValidationError("Channel identifier is required")

        try:
            self._validate_member_data(member_data)
            response = self._make_request('auth', 'register', payload=member_data)
            data = response.json()

            if token := self._extract_token(data):
                self._update_token(token)
                logger.info("Registration successful")
                return True, data
            return False, {"message": "Registration failed: No token received"}

        except ValidationError as e:
            return False, {"message": str(e)}
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}")
            return False, {"message": str(e)}

    def refresh_token(self, channel_identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Refresh authentication token"""
        if not channel_identifier:
            raise ValidationError("Channel identifier is required")

        try:
            response = self._make_request(
                'auth', 'login',
                payload={"phone": channel_identifier}  # Map to phone for API compatibility
            )
            data = response.json()

            if token := self._extract_token(data):
                self._update_token(token)
                logger.info("Token refresh successful")
                return True, data
            return False, {"message": "Token refresh failed: No token received"}

        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return False, {"message": str(e)}
