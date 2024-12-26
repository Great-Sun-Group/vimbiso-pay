import logging
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

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
        self._phone: Optional[str] = None  # Store phone for token refresh
        logger.debug(f"Initialized BaseCredExService with base_url: {self.config.base_url}")

    def _extract_error_message(self, response: requests.Response) -> str:
        """Extract the most user-friendly error message from a response"""
        try:
            # Try to parse response as JSON
            try:
                error_data = response.json()
                logger.debug(f"Response content: {error_data}")
            except Exception:
                logger.debug(f"Non-JSON response: {response.text}")
                error_data = {}

            # Direct message in response
            if error_data.get("message"):
                return error_data["message"]

            # Check for business logic errors in action.details
            action = error_data.get("data", {}).get("action", {})
            if action.get("type") == "CREDEX_CREATE_FAILED":
                details = action.get("details", {})
                if details.get("reason"):
                    return details["reason"]

            # Check for error details
            if error_data.get("error"):
                return error_data["error"]

            # Check for specific error conditions
            if "Required field missing" in str(error_data):
                return "Please check your input and try again."
            elif response.status_code == 404:
                # Check if this is a member not found case
                if "Member not found" in str(error_data):
                    return "Member not found"
                return "Recipient account not found. Please check the handle and try again."
            elif response.status_code == 403:
                return "You don't have permission to perform this action."
            elif response.status_code == 502:
                return "The service is temporarily unavailable. Please try again in a few minutes."
            elif response.status_code >= 500:
                return "The service is experiencing technical difficulties. Please try again later."

            # Last resort - return raw response content if nothing else found
            if error_data:
                return str(error_data)

            return f"Server error {response.status_code}. Please try again."
        except Exception as e:
            logger.error(f"Error extracting error message: {str(e)}")
            return f"Server error {response.status_code}. Please try again."

    def _make_request(
        self,
        group: str,
        action: str,
        method: str = "POST",
        payload: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Make an HTTP request to the CredEx API using endpoint groups"""
        from .config import CredExEndpoints

        # Get endpoint path and auth requirement
        path = CredExEndpoints.get_path(group, action)
        requires_auth = CredExEndpoints.requires_auth(group, action)

        # Build request
        url = self.config.get_url(path)
        headers = self.config.get_headers(self._jwt_token if requires_auth else None)

        logger.info(f"Making {method} request to {group}/{action}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Payload: {payload}")

        try:
            # Make request
            response = requests.request(method, url, headers=headers, json=payload)
            logger.debug(f"Response status: {response.status_code}")

            # Handle token refresh
            if new_token := response.headers.get('Authorization'):
                self._update_token(new_token)

            # Handle 401 for auth-required endpoints
            if response.status_code == 401 and requires_auth and payload and "phone" in payload:
                logger.warning("Auth failed, attempting refresh")
                if refreshed_token := self._refresh_token(payload["phone"]):
                    headers = self.config.get_headers(refreshed_token)
                    response = requests.request(method, url, headers=headers, json=payload)

            # Handle errors
            if response.status_code >= 400 and requires_auth:
                raise TransactionError(self._extract_error_message(response))

            return response

        except requests.exceptions.RequestException as e:
            raise TransactionError(f"Network error: {str(e)}")

    def _refresh_token(self, phone: str) -> Optional[str]:
        """Refresh authentication token"""
        from .auth import CredExAuthService
        auth_service = CredExAuthService(config=self.config)
        success, _ = auth_service.login(phone)
        if success:
            token = auth_service._jwt_token
            self._update_token(token)
            return token
        return None

    def _update_token(self, token: str) -> None:
        """Update token in service and state"""
        self._jwt_token = token
        if hasattr(self, '_parent_service') and hasattr(self._parent_service, 'user'):
            self._parent_service.user.state.update_state({"jwt_token": token})

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
                    error_msg = self._extract_error_message(response)
                logger.error(error_msg)  # Log the actual error message without prefix
                raise TransactionError(error_msg)

            return data

        except ValueError as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            raise TransactionError("Invalid response from server. Please try again.")

    def _handle_error_response(self, response: requests.Response, error_mapping: Dict[int, str]) -> Tuple[bool, Dict[str, Any]]:
        """Handle error response with proper error mapping"""
        try:
            error_msg = self._extract_error_message(response)
            return False, {"message": error_msg}
        except Exception as e:
            logger.error(f"Error handling error response: {str(e)}")
            return False, {"message": str(e)}

    @property
    def jwt_token(self) -> Optional[str]:
        """Get the current JWT token"""
        return self._jwt_token

    @jwt_token.setter
    def jwt_token(self, value: str):
        """Set the JWT token"""
        self._update_token(value)
