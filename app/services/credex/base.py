import logging
from typing import Any, Dict, Optional

import requests

from .config import CredExConfig
from .exceptions import (
    APIError,
    AuthenticationError,
    NetworkError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class BaseCredExService:
    """Base class with core CredEx service functionality"""

    def __init__(self, config: Optional[CredExConfig] = None):
        """Initialize the base service

        Args:
            config: Service configuration. If not provided, loads from environment.
        """
        self.config = config or CredExConfig.from_env()
        self._jwt_token: Optional[str] = None

    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        payload: Optional[Dict[str, Any]] = None,
        require_auth: bool = True,
    ) -> requests.Response:
        """Make an HTTP request to the CredEx API"""
        url = self.config.get_url(endpoint)
        headers = self.config.get_headers(self._jwt_token if require_auth else None)

        try:
            logger.debug(f"Making {method} request to {url}")
            response = requests.request(method, url, headers=headers, json=payload)

            if response.status_code == 401 and require_auth:
                logger.warning("Authentication failed, attempting to refresh token")
                if payload and "phone" in payload:
                    # This will be implemented in auth.py
                    from .auth import CredExAuthService
                    auth_service = CredExAuthService(config=self.config)
                    success, _ = auth_service.login(payload["phone"])
                    if success:
                        self._jwt_token = auth_service._jwt_token
                        headers = self.config.get_headers(self._jwt_token)
                        response = requests.request(method, url, headers=headers, json=payload)
                    else:
                        raise AuthenticationError("Failed to refresh authentication token")

            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during API request: {str(e)}")
            raise NetworkError(f"Failed to connect to CredEx API: {str(e)}")

    def _validate_response(
        self, response: requests.Response, error_mapping: Optional[Dict[int, str]] = None
    ) -> Dict[str, Any]:
        """Validate API response"""
        try:
            if not response.headers.get("Content-Type", "").startswith("application/json"):
                raise ValidationError(f"Unexpected Content-Type: {response.headers.get('Content-Type')}")

            data = response.json()

            if response.status_code >= 400:
                error_msg = error_mapping.get(response.status_code) if error_mapping else None
                error_msg = error_msg or data.get("message") or f"API error {response.status_code}"
                logger.error(f"API error: {error_msg}")
                raise APIError(error_msg)

            return data

        except ValueError as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            raise ValidationError(f"Invalid API response: {str(e)}")

    @property
    def jwt_token(self) -> Optional[str]:
        """Get the current JWT token"""
        return self._jwt_token

    @jwt_token.setter
    def jwt_token(self, value: str):
        """Set the JWT token"""
        self._jwt_token = value
