"""Base API functionality using pure functions"""
import base64
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urljoin

import requests
from decouple import config
from requests.exceptions import RequestException

from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import SystemException
from core.utils.state_validator import StateValidator
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
TIMEOUT = 30  # seconds
BASE_URL = config('MYCREDEX_APP_URL')
if not BASE_URL.endswith('/'):
    BASE_URL += '/'


def get_headers(state_manager: Any, include_auth: bool = True) -> Dict[str, str]:
    """Get request headers with authentication"""
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


def make_api_request(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    method: str = "POST",
    retry_auth: bool = True,
    state_manager: Optional[Any] = None
) -> Dict:
    """Make API request with logging, validation and error handling"""
    try:
        # Validate request parameters
        validation = validate_request_params(url, headers, payload)
        if "error" in validation:
            return validation

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
                    # Create bot service for login
                    from services.whatsapp.bot_service import get_bot_service
                    bot_service = get_bot_service(state_manager)
                    success, _ = login(bot_service)
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

    # Log detailed error info
    logger.error({
        "operation": operation,
        "status_code": response.status_code,
        "error_message": error_msg,
        "response_headers": dict(response.headers),
        "response_body": response.text[:1000]  # Truncate long responses
    })

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
