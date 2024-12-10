import logging
import sys
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

import requests

from core.transactions.exceptions import TransactionError

if TYPE_CHECKING:
    from .config import CredExConfig

# Configure logging to output to stdout with DEBUG level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


class BaseCredExService:
    """Base class with core CredEx service functionality"""

    def __init__(self, config: Optional['CredExConfig'] = None):
        """Initialize the base service

        Args:
            config: Service configuration. If not provided, loads from environment.
        """
        # Import here to avoid circular imports
        from .config import CredExConfig
        self.config = config or CredExConfig.from_env()
        self._jwt_token: Optional[str] = None
        logger.debug(f"Initialized BaseCredExService with base_url: {self.config.base_url}")

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

        logger.info(f"Making {method} request to {endpoint}")
        logger.debug(f"Full URL: {url}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Payload: {payload}")

        try:
            response = requests.request(method, url, headers=headers, json=payload)

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content: {response.text}")

            if response.status_code == 401 and require_auth:
                logger.warning("Authentication failed, attempting to refresh token")
                if payload and "phone" in payload:
                    # This will be implemented in auth.py
                    from .auth import CredExAuthService
                    auth_service = CredExAuthService(config=self.config)
                    logger.debug(f"Attempting to refresh token for phone: {payload['phone']}")
                    success, msg = auth_service.login(payload["phone"])
                    logger.debug(f"Token refresh result: success={success}, msg={msg}")
                    if success:
                        # Update token and propagate to parent service if available
                        self._jwt_token = auth_service._jwt_token
                        if hasattr(self, '_parent_service'):
                            self._parent_service.jwt_token = self._jwt_token
                        headers = self.config.get_headers(self._jwt_token)
                        logger.debug("Making request with refreshed token")
                        response = requests.request(method, url, headers=headers, json=payload)
                        logger.debug(f"Refresh response status: {response.status_code}")
                        logger.debug(f"Refresh response content: {response.text}")
                    else:
                        raise TransactionError("Authentication failed. Please try again.")

            # Check for error responses
            if response.status_code >= 400:
                error_data = response.json() if response.headers.get("Content-Type") == "application/json" else {}
                error_msg = error_data.get("message", f"API error {response.status_code}")

                if "Required field missing" in error_msg:
                    error_msg = "Please check your input and try again."
                elif response.status_code == 404:
                    error_msg = "Recipient account not found. Please check the handle and try again."
                elif response.status_code == 403:
                    error_msg = "You don't have permission to perform this action."
                elif response.status_code >= 500:
                    error_msg = "Server error. Please try again later."

                logger.error(f"API error: {error_msg}")
                raise TransactionError(error_msg)

            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during API request: {str(e)}")
            raise TransactionError("Network error. Please check your connection and try again.")

    def _validate_response(
        self, response: requests.Response, error_mapping: Optional[Dict[int, str]] = None
    ) -> Dict[str, Any]:
        """Validate API response"""
        try:
            content_type = response.headers.get("Content-Type", "")
            logger.info(f"Validating API response for status code {response.status_code}")
            logger.debug(f"Content-Type: {content_type}")
            logger.debug(f"Response text: {response.text}")

            if "application/json" not in content_type.lower():
                logger.error(f"Unexpected Content-Type: {content_type}")
                raise TransactionError("Invalid response from server. Please try again.")

            try:
                data = response.json()
                logger.debug(f"Parsed JSON response: {data}")
            except ValueError:
                logger.error(f"Failed to parse response as JSON: {response.text}")
                raise TransactionError("Invalid response format. Please try again.")

            if response.status_code >= 400:
                error_msg = error_mapping.get(response.status_code) if error_mapping else None
                if not error_msg:
                    # Check for field validation errors
                    if "Required field missing" in data.get("message", ""):
                        error_msg = "Please check your input and try again."
                    else:
                        error_msg = data.get("message") or f"API error {response.status_code}"
                logger.error(f"API error: {error_msg}")
                raise TransactionError(error_msg)

            return data

        except ValueError as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            raise TransactionError("Invalid response from server. Please try again.")

    def _handle_error_response(self, response: requests.Response, error_mapping: Dict[int, str]) -> Tuple[bool, Dict[str, Any]]:
        """Handle error response with proper error mapping"""
        try:
            error_msg = error_mapping.get(response.status_code, "Unknown error")
            if response.headers.get("Content-Type", "").lower() == "application/json":
                data = response.json()
                api_msg = data.get("message", "")
                # Check for field validation errors
                if "Required field missing" in api_msg:
                    error_msg = "Please check your input and try again."
                elif api_msg:
                    error_msg = api_msg
            return False, {"error": error_msg}
        except Exception as e:
            logger.error(f"Error handling error response: {str(e)}")
            return False, {"error": str(e)}

    @property
    def jwt_token(self) -> Optional[str]:
        """Get the current JWT token"""
        return self._jwt_token

    @jwt_token.setter
    def jwt_token(self, value: str):
        """Set the JWT token"""
        logger.debug("Setting new JWT token")
        self._jwt_token = value
