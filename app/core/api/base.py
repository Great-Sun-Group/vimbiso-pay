"""Base API functionality using pure functions"""
import base64
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

import requests
from core.state.interface import StateManagerInterface
from core.error.handler import ErrorHandler
from core.error.exceptions import SystemException
from core.state.validator import StateValidator
from decouple import config
from requests.exceptions import RequestException

from . import api_response

logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
TIMEOUT = 30  # seconds
BASE_URL = config('MYCREDEX_APP_URL')
if not BASE_URL.endswith('/'):
    BASE_URL += '/'


def handle_api_response(
    response: requests.Response,
    state_manager: StateManagerInterface
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Handle API response with state updates

    All API responses include:
    1. dashboard section -> Member state after operation
    2. action section -> Operation results and details

    Args:
        response: API response to handle
        state_manager: State manager instance

    Returns:
        Tuple[Dict[str, Any], Optional[str]]: Response data and optional error
    """
    try:
        # Process response first
        response_data = process_api_response(response)
        if "error" in response_data:
            return response_data, response_data["error"].get("message")

        # Update state with API response data
        success, error = api_response.update_state_from_response(
            api_response=response_data,
            state_manager=state_manager
        )
        if not success:
            logger.error(f"Failed to update state: {error}")

        if not success:
            return response_data, error

        return response_data, None
    except Exception as e:
        return {"error": str(e)}, str(e)


def get_headers(state_manager: StateManagerInterface, url: str) -> Dict[str, str]:
    """Get request headers with authentication if required

    Args:
        state_manager: State manager instance
        url: Request URL to check if auth is required

    Returns:
        Dict[str, str]: Headers with auth token if needed
    """
    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
    }

    # Check if endpoint needs auth
    if is_auth_required(url):
        # Get required state fields with validation at boundary
        required_fields = {"channel"}
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

        # Get auth token from component data (components can store their own data in component_data.data)
        component_data = state_manager.get_state_value("component_data", {})
        action_data = component_data.get("action", {})
        jwt_token = action_data.get("details", {}).get("token")

        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        else:
            logger.warning("No JWT token available for authenticated request")

    return headers


def validate_request_params(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any]
) -> Dict:
    """Validate request parameters before making API call"""
    if not url:
        return ErrorHandler.handle_system_error(
            code="INVALID_URL",
            service="api_client",
            action="validate_params",
            message="URL cannot be empty"
        )

    if not isinstance(headers, dict):
        return ErrorHandler.handle_system_error(
            code="INVALID_HEADERS",
            service="api_client",
            action="validate_params",
            message="Headers must be a dictionary"
        )

    if not isinstance(payload, dict):
        return ErrorHandler.handle_system_error(
            code="INVALID_PAYLOAD",
            service="api_client",
            action="validate_params",
            message="Payload must be a dictionary"
        )

    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        url = urljoin(BASE_URL, url)
        if not url.startswith(('http://', 'https://')):
            return ErrorHandler.handle_system_error(
                code="INVALID_URL_FORMAT",
                service="api_client",
                action="validate_params",
                message=f"Invalid URL format: {url}"
            )

    return {"valid": True}


def is_auth_required(url: str) -> bool:
    """Check if URL requires authentication"""
    # Strip any leading/trailing slashes and base URL
    endpoint = url.rstrip('/').split('/')[-1]
    return endpoint not in ['login', 'onboard']


def make_api_request(
    url: str,
    payload: Dict[str, Any],
    method: str = "POST",
    retry_auth: bool = True,
    state_manager: Optional[StateManagerInterface] = None
) -> Dict:
    """Make API request with logging, validation and error handling"""
    try:
        # Ensure URL is absolute
        if not url.startswith(('http://', 'https://')):
            url = urljoin(BASE_URL, url)

        # Check if endpoint requires auth
        requires_auth = is_auth_required(url)
        if requires_auth and not state_manager:
            return ErrorHandler.handle_system_error(
                code="AUTH_ERROR",
                service="api_client",
                action="validate_auth",
                message="State manager required for authenticated request"
            )

        # Get headers with auth if needed
        headers = get_headers(state_manager, url) if state_manager else {}

        # Validate request parameters
        validation = validate_request_params(url, headers, payload)
        if "error" in validation:
            return validation

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Making API request to {url}")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Payload: {payload}")

        retries = 0
        while retries < MAX_RETRIES:
            try:
                # Try request with current headers
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=payload,
                    timeout=TIMEOUT
                )

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"API Response Status: {response.status_code}")
                    logger.debug(f"API Response Headers: {response.headers}")

                # Handle auth errors
                if requires_auth and (
                    # No token in headers
                    ("Authorization" not in headers and retry_auth) or
                    # Or got 401 response
                    (response.status_code == 401 and retry_auth)
                ):
                    if not state_manager:
                        return ErrorHandler.handle_system_error(
                            code="AUTH_ERROR",
                            service="api_client",
                            action="validate_auth",
                            message="State manager required for authenticated request"
                        )

                    logger.warning("Auth error, attempting login")
                    from services.whatsapp.bot_service import get_bot_service
                    from .login import login
                    bot_service = get_bot_service(state_manager)
                    success, _ = login(bot_service)
                    if not success:
                        return ErrorHandler.handle_system_error(
                            code="AUTH_ERROR",
                            service="api_client",
                            action="refresh_token",
                            message="Failed to refresh auth token"
                        )

                    # Retry with new token
                    headers = get_headers(state_manager, url)
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
                raise SystemException(
                    message=f"Request failed after {MAX_RETRIES} retries: {str(e)}",
                    code="REQUEST_FAILED",
                    service="api_client",
                    action=f"{method}_{url}"
                )

        raise SystemException(
            message=f"Failed after {MAX_RETRIES} retries",
            code="MAX_RETRIES_EXCEEDED",
            service="api_client",
            action=f"{method}_{url}"
        )

    except Exception as e:
        raise SystemException(
            message=f"Error making API request: {str(e)}",
            code="REQUEST_ERROR",
            service="api_client",
            action=f"{method}_{url}"
        )


def process_api_response(
    response: requests.Response,
    expected_status_codes: Optional[list] = None
) -> Dict[str, Any]:
    """Process API response with validation"""
    if expected_status_codes is None:
        expected_status_codes = [200]

    try:
        # Validate status code
        if response.status_code not in expected_status_codes:
            return ErrorHandler.handle_system_error(
                code="INVALID_STATUS",
                service="api_client",
                action="process_response",
                message=f"Unexpected status code: {response.status_code}. Expected one of: {expected_status_codes}"
            )

        # Validate content type
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return ErrorHandler.handle_system_error(
                code="INVALID_CONTENT_TYPE",
                service="api_client",
                action="process_response",
                message=f"Received unexpected Content-Type: {content_type}"
            )

        # Parse and validate response
        data = response.json()
        if not isinstance(data, dict):
            return ErrorHandler.handle_system_error(
                code="INVALID_RESPONSE",
                service="api_client",
                action="process_response",
                message="Response data must be a dictionary"
            )
        return data

    except ValueError as e:
        return ErrorHandler.handle_system_error(
            code="PARSE_ERROR",
            service="api_client",
            action="process_response",
            message=f"Failed to parse response JSON: {str(e)}"
        )


def handle_error_response(
    operation: str,
    response: requests.Response,
    custom_message: str = None
) -> Dict:
    """Handle error response with logging"""
    # Handle 502 errors specifically
    if response.status_code == 502:
        error_msg = "❌ Sorry, the server is temporarily down (502). Please try again soon."
        logger.error(f"{operation} failed: Server temporarily unavailable (502)")
    else:
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

    # Log error summary
    logger.error(f"{operation} failed: {response.status_code} - {error_msg}")

    # Create validation state with response details
    validation_state = {
        "attempts": 1,
        "last_attempt": datetime.utcnow().isoformat(),
        "status_code": response.status_code,
        "response": error_data if "error_data" in locals() else response.text
    }

    return ErrorHandler.handle_system_error(
        code="API_ERROR",
        service="api_client",
        action=operation,
        message=error_msg,
        validation_state=validation_state
    )


def get_basic_auth_header(channel_identifier: str) -> str:
    """Generate basic auth header using channel identifier"""
    if not channel_identifier:
        raise ValueError("Channel identifier cannot be empty")

    credentials = f"{channel_identifier}:{channel_identifier}"
    encoded_credentials = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")
    return f"Basic {encoded_credentials}"
