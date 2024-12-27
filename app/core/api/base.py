"""Base API functionality using pure functions"""
import base64
import logging
import time
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urljoin

import requests
from decouple import config
from django.core.cache import cache
from requests.exceptions import RequestException

from core.utils.state_validator import StateValidator
from ..utils.utils import send_whatsapp_message

logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
TIMEOUT = 30  # seconds
BASE_URL = config('MYCREDEX_APP_URL')
if not BASE_URL.endswith('/'):
    BASE_URL += '/'


def get_headers(state_manager: Any, include_auth: bool = True) -> Dict[str, str]:
    """
    Get request headers with authentication

    Args:
        state_manager: State manager instance
        include_auth: Whether to include authentication headers
    """
    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
    }

    if include_auth:
        # Get required state fields with validation at boundary
        required_fields = {"channel", "jwt_token"}
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        # Validate at boundary
        validation = StateValidator.validate_state(current_state)
        if not validation.is_valid:
            logger.error(f"Invalid state: {validation.error_message}")
            return headers

        channel = current_state["channel"]
        if not isinstance(channel, dict) or not channel.get("identifier"):
            logger.error("Invalid channel structure")
            return headers

        jwt_token = state_manager.get("jwt_token")
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        else:
            logger.warning("No JWT token available for authenticated request")

    return headers


def validate_request_params(
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
        url = urljoin(BASE_URL, url)
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL format: {url}")


def make_api_request(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    method: str = "POST",
    retry_auth: bool = True,
    state_manager: Optional[Any] = None
) -> requests.Response:
    """
    Make API request with logging, validation and error handling

    Args:
        url: API endpoint URL
        headers: Request headers
        payload: Request payload
        method: HTTP method
        retry_auth: Whether to retry with fresh auth token on 401
        state_manager: Optional state manager for auth refresh
    """
    try:
        # Validate request parameters
        validate_request_params(url, headers, payload)

        # Ensure URL is absolute
        if not url.startswith(('http://', 'https://')):
            url = urljoin(BASE_URL, url)

        logger.info(f"Sending API request to: {url}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Payload: {payload}")

        retries = 0
        while retries < MAX_RETRIES:
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=payload,
                    timeout=TIMEOUT
                )

                logger.info(f"API Response Status Code: {response.status_code}")
                logger.debug(f"API Response Headers: {response.headers}")
                logger.debug(f"API Response Content: {response.text[:500]}...")

                # Handle 401 with retry
                if response.status_code == 401 and retry_auth and state_manager:
                    logger.warning("Received 401, attempting to refresh auth token")
                    from .auth import login
                    success, _ = login(BASE_URL, state_manager)
                    if success:
                        headers = get_headers(state_manager)  # Get fresh headers
                        retries += 1
                        time.sleep(RETRY_DELAY)
                        continue

                return response

            except RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                retries += 1
                if retries < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                raise

        raise Exception(f"Failed after {MAX_RETRIES} retries")

    except Exception as e:
        logger.error(f"Error making API request: {str(e)}")
        raise


def process_api_response(
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


def handle_error_response(
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


def get_basic_auth_header(channel_identifier: str) -> str:
    """Generate basic auth header using channel identifier"""
    if not channel_identifier:
        raise ValueError("Channel identifier cannot be empty")

    credentials = f"{channel_identifier}:{channel_identifier}"
    encoded_credentials = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")
    return f"Basic {encoded_credentials}"


def send_delay_message(state_manager: Any) -> None:
    """Send delay message to user"""
    # Get required state fields with validation at boundary
    validation = StateValidator.validate_before_access(
        {
            "stage": state_manager.get("stage"),
            "channel": state_manager.get("channel")
        },
        {"stage", "channel"}
    )
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return

    stage = state_manager.get("stage")
    channel = state_manager.get("channel", {})
    channel_id = channel.get("identifier")

    if (
        stage != "handle_action_register"
        and not cache.get(f"{channel_id}_interracted")
    ):
        try:
            send_whatsapp_message(payload={
                "messaging_product": "whatsapp",
                "preview_url": False,
                "recipient_type": "individual",
                "to": channel_id,
                "type": "text",
                "text": {"body": "Please wait while we process your request..."},
            })

            cache.set(f"{channel_id}_interracted", True, 60 * 15)
        except Exception as e:
            logger.error(f"Failed to send delay message: {str(e)}")


def send_first_message(state_manager: Any) -> None:
    """Send welcome message to user"""
    try:
        # Validate channel info at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            logger.error(f"Invalid state: {validation.error_message}")
            return

        channel = state_manager.get("channel", {})
        channel_id = channel.get("identifier")

        first_message = "Welcome to CredEx! How can I assist you today?"
        send_whatsapp_message(payload={
            "messaging_product": "whatsapp",
            "preview_url": False,
            "recipient_type": "individual",
            "to": channel_id,
            "type": "text",
            "text": {"body": first_message},
        })
    except Exception as e:
        logger.error(f"Failed to send welcome message: {str(e)}")


def handle_reset_and_init(state_manager: Any, reset: bool, silent: bool, init: bool) -> None:
    """Handle reset and initialization messages"""
    if reset and not silent or init:
        send_delay_message(state_manager)
        send_first_message(state_manager)
