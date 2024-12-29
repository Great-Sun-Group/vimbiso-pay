"""CredEx authentication service using pure functions"""
import logging
from typing import Any, Dict, Optional, Tuple

from .base import make_credex_request
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


def validate_member_data(member_data: Dict[str, Any]) -> None:
    """Validate member registration business rules"""
    # Only validate business rules
    valid_denoms = {"CXX", "CAD", "USD", "XAU", "ZWG"}
    denom = member_data.get("defaultDenom")
    if denom not in valid_denoms:
        raise ValidationError(f"Invalid defaultDenom. Must be one of: {', '.join(valid_denoms)}")

    # Validate name lengths (business rule)
    for field in ["firstname", "lastname"]:
        length = len(str(member_data.get(field, "")).strip())
        if not (3 <= length <= 50):
            raise ValidationError(f"{field.title()} must be between 3 and 50 characters")


def login(channel_identifier: str, jwt_token: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """Authenticate user enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Log login attempt
        logger.info(f"Attempting login for channel {channel_identifier}")

        # Make API request
        response = make_credex_request(
            'auth', 'login',
            payload={"phone": channel_identifier},
            jwt_token=jwt_token
        )

        if not response.ok:
            return False, {"message": f"Login request failed: {response.status_code}"}

        try:
            return True, response.json()
        except ValueError:
            return False, {"message": "Invalid response format"}

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return False, {"message": "Login failed due to system error"}


def register_member(member_data: Dict[str, Any], channel_identifier: str, jwt_token: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """Register new member enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate business rules only
        validate_member_data(member_data)

        # Log registration attempt
        logger.info(f"Attempting registration for channel {channel_identifier}")

        # Make API request
        response = make_credex_request(
            'auth', 'register',
            payload=member_data,
            jwt_token=jwt_token
        )

        if not response.ok:
            return False, {"message": f"Registration request failed: {response.status_code}"}

        try:
            return True, response.json()
        except ValueError:
            return False, {"message": "Invalid response format"}

    except ValidationError as e:
        logger.error(f"Registration validation error: {str(e)}")
        return False, {"message": str(e)}
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return False, {"message": "Registration failed due to system error"}


def refresh_token(channel_identifier: str, jwt_token: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """Refresh authentication token enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Log refresh attempt
        logger.info(f"Attempting token refresh for channel {channel_identifier}")

        # Make API request
        response = make_credex_request(
            'auth', 'login',
            payload={"phone": channel_identifier},
            jwt_token=jwt_token
        )

        if not response.ok:
            return False, {"message": f"Token refresh failed: {response.status_code}"}

        try:
            return True, response.json()
        except ValueError:
            return False, {"message": "Invalid response format"}

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return False, {"message": "Token refresh failed due to system error"}


def get_dashboard(channel_identifier: str, jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
    """Get dashboard data from login response enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Make API request (reuse login endpoint)
        response = make_credex_request(
            'auth', 'login',
            payload={"phone": channel_identifier},
            jwt_token=jwt_token
        )

        if not response.ok:
            return False, {"message": f"Dashboard request failed: {response.status_code}"}

        try:
            return True, response.json()
        except ValueError:
            return False, {"message": "Invalid response format"}

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return False, {"message": "Failed to get dashboard data"}
