"""Base API client implementation"""
import base64
import logging
import time
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urljoin

import requests
from decouple import config
from django.core.cache import cache
from requests.exceptions import RequestException
from services.whatsapp.types import BotServiceInterface
from ..config.constants import CachedUser
from ..utils.utils import CredexWhatsappService

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """Base class for API interactions"""
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    TIMEOUT = 30  # seconds

    def __init__(self, bot_service: BotServiceInterface):
        self.bot_service = bot_service
        self.base_url = config('MYCREDEX_APP_URL')
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        logger.info(f"Base URL: {self.base_url}")

    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """
        Get request headers with authentication

        Args:
            include_auth: Whether to include authentication headers
        """
        headers = {
            "Content-Type": "application/json",
            "x-client-api-key": config("CLIENT_API_KEY"),
        }

        if include_auth:
            user = CachedUser(self.bot_service.user.mobile_number)
            if user.jwt_token:
                headers["Authorization"] = f"Bearer {user.jwt_token}"
            else:
                logger.warning("No JWT token available for authenticated request")

        return headers

    def _validate_request_params(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> None:
        """Validate request parameters before making API call"""
        if not url:
            raise ValueError("URL cannot be empty")

        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary")

        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dictionary")

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL format: {url}")

    def _make_api_request(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        method: str = "POST",
        retry_auth: bool = True
    ) -> requests.Response:
        """
        Make API request with logging, validation and error handling

        Args:
            url: API endpoint URL
            headers: Request headers
            payload: Request payload
            method: HTTP method
            retry_auth: Whether to retry with fresh auth token on 401
        """
        try:
            # Validate request parameters
            self._validate_request_params(url, headers, payload)

            # Ensure URL is absolute
            if not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)

            logger.info(f"Sending API request to: {url}")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Payload: {payload}")

            retries = 0
            while retries < self.MAX_RETRIES:
                try:
                    response = requests.request(
                        method,
                        url,
                        headers=headers,
                        json=payload,
                        timeout=self.TIMEOUT
                    )

                    logger.info(f"API Response Status Code: {response.status_code}")
                    logger.debug(f"API Response Headers: {response.headers}")
                    logger.debug(f"API Response Content: {response.text[:500]}...")

                    # Handle 401 with retry
                    if response.status_code == 401 and retry_auth:
                        logger.warning("Received 401, attempting to refresh auth token")
                        if self._handle_auth_refresh():
                            headers = self._get_headers()  # Get fresh headers
                            retries += 1
                            time.sleep(self.RETRY_DELAY)
                            continue

                    return response

                except RequestException as e:
                    logger.error(f"Request failed: {str(e)}")
                    retries += 1
                    if retries < self.MAX_RETRIES:
                        time.sleep(self.RETRY_DELAY)
                        continue
                    raise

            raise Exception(f"Failed after {self.MAX_RETRIES} retries")

        except Exception as e:
            logger.exception(f"Error making API request: {str(e)}")
            raise

    def _handle_auth_refresh(self) -> bool:
        """
        Handle authentication refresh on 401 errors
        Returns True if auth was refreshed successfully
        """
        try:
            from .auth import AuthManager
            auth_manager = AuthManager(self.bot_service)
            success, _ = auth_manager.login()
            return success
        except Exception as e:
            logger.error(f"Failed to refresh authentication: {str(e)}")
            return False

    def _process_api_response(
        self,
        response: requests.Response,
        expected_status_codes: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Process API response with validation

        Args:
            response: Response object to process
            expected_status_codes: List of valid status codes, defaults to [200]
        """
        if expected_status_codes is None:
            expected_status_codes = [200]

        # Validate status code
        if response.status_code not in expected_status_codes:
            raise ValueError(
                f"Unexpected status code: {response.status_code}. "
                f"Expected one of: {expected_status_codes}"
            )

        # Validate content type
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise ValueError(f"Received unexpected Content-Type: {content_type}")

        # Parse and validate response
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Response data must be a dictionary")
            return data
        except ValueError as e:
            logger.error(f"Failed to parse response JSON: {str(e)}")
            raise

    def _handle_error_response(
        self,
        operation: str,
        response: requests.Response,
        custom_message: str = None
    ) -> Tuple[bool, str]:
        """
        Handle error response with logging

        Args:
            operation: Name of the operation that failed
            response: Response object containing error
            custom_message: Optional custom error message
        """
        try:
            error_data = response.json()
            error_msg = custom_message or error_data.get(
                "message",
                error_data.get("error", f"{operation} failed")
            )
        except ValueError:
            error_msg = custom_message or f"{operation} failed"

        logger.error(
            f"{operation} failed: {response.status_code}. Response: {response.text}"
        )

        # Log detailed error info
        logger.error({
            "operation": operation,
            "status_code": response.status_code,
            "error_message": error_msg,
            "response_headers": dict(response.headers),
            "response_body": response.text[:1000]  # Truncate long responses
        })

        return False, error_msg

    @staticmethod
    def _get_basic_auth_header(phone_number: str) -> str:
        """Generate basic auth header"""
        if not phone_number:
            raise ValueError("Phone number cannot be empty")

        credentials = f"{phone_number}:{phone_number}"
        encoded_credentials = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")
        return f"Basic {encoded_credentials}"

    def _send_delay_message(self) -> None:
        """Send delay message to user"""
        if (
            self.bot_service.state.stage != "handle_action_register"
            and not cache.get(f"{self.bot_service.user.mobile_number}_interracted")
        ):
            try:
                CredexWhatsappService(
                    payload={
                        "messaging_product": "whatsapp",
                        "preview_url": False,
                        "recipient_type": "individual",
                        "to": self.bot_service.user.mobile_number,
                        "type": "text",
                        "text": {"body": "Please wait while we process your request..."},
                    }
                ).send_message()

                cache.set(
                    f"{self.bot_service.user.mobile_number}_interracted",
                    True,
                    60 * 15
                )
            except Exception as e:
                logger.error(f"Failed to send delay message: {str(e)}")

    def _send_first_message(self) -> None:
        """Send welcome message to user"""
        try:
            first_message = "Welcome to CredEx! How can I assist you today?"
            CredexWhatsappService(
                payload={
                    "messaging_product": "whatsapp",
                    "preview_url": False,
                    "recipient_type": "individual",
                    "to": self.bot_service.user.mobile_number,
                    "type": "text",
                    "text": {"body": first_message},
                }
            ).send_message()
        except Exception as e:
            logger.error(f"Failed to send welcome message: {str(e)}")

    def _handle_reset_and_init(self, reset: bool, silent: bool, init: bool) -> None:
        """Handle reset and initialization messages"""
        if reset and not silent or init:
            self._send_delay_message()
            self._send_first_message()