"""Base CredEx functionality using pure functions"""
import logging
import sys
from typing import Any, Dict, Optional, Tuple

import requests
from core.transactions.exceptions import TransactionError

# Configure logging to output to stdout with DEBUG level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def extract_error_message(response: requests.Response) -> str:
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


def make_credex_request(
    group: str,
    action: str,
    method: str = "POST",
    payload: Optional[Dict[str, Any]] = None,
    jwt_token: Optional[str] = None,
) -> requests.Response:
    """Make an HTTP request to the CredEx API using endpoint groups"""
    from .config import CredExConfig, CredExEndpoints

    config = CredExConfig.from_env()

    # Get endpoint path and auth requirement
    path = CredExEndpoints.get_path(group, action)
    requires_auth = CredExEndpoints.requires_auth(group, action)

    # Build request
    url = config.get_url(path)
    headers = config.get_headers(jwt_token if requires_auth else None)

    logger.info(f"Making {method} request to {group}/{action}")
    logger.debug(f"URL: {url}")
    logger.debug(f"Payload: {payload}")

    try:
        # Make request
        response = requests.request(method, url, headers=headers, json=payload)
        logger.debug(f"Response status: {response.status_code}")

        # Handle 401 for auth-required endpoints
        if response.status_code == 401 and requires_auth and payload and "phone" in payload:
            logger.warning("Auth failed, attempting refresh")
            # Return 401 to let state manager handle refresh
            return response

        # Handle errors
        if response.status_code >= 400 and requires_auth:
            raise TransactionError(extract_error_message(response))

        return response

    except requests.exceptions.RequestException as e:
        raise TransactionError(f"Network error: {str(e)}")


def validate_response(
    response: requests.Response,
    error_mapping: Optional[Dict[int, str]] = None
) -> Dict[str, Any]:
    """Validate API response enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate input
        if not isinstance(response, requests.Response):
            raise ValueError("Invalid response object")

        # Get response metadata
        content_type = response.headers.get("Content-Type", "")
        status_code = response.status_code

        logger.info(f"Validating API response with status code {status_code}")
        logger.debug(f"Content-Type: {content_type}")
        logger.debug(f"Response text: {response.text}")

        # Validate content type
        if "application/json" not in content_type.lower():
            error_msg = f"Unexpected Content-Type: {content_type}"
            logger.error(error_msg)
            raise TransactionError("Invalid response format from server")

        # Parse response data
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Response data must be a dictionary")
            logger.debug(f"Parsed JSON response: {data}")
        except ValueError as err:
            logger.error(f"Failed to parse response as JSON: {str(err)}")
            raise TransactionError("Invalid response format from server")

        # Handle error responses
        if status_code >= 400:
            error_msg = error_mapping.get(status_code) if error_mapping else None
            if not error_msg:
                error_msg = extract_error_message(response)
            logger.error(f"API error response: {error_msg}")
            raise TransactionError(error_msg)

        return data

    except ValueError as e:
        logger.error(f"Response validation error: {str(e)}")
        raise TransactionError("Invalid response format from server")
    except Exception as e:
        logger.error(f"Unexpected error validating response: {str(e)}")
        raise TransactionError("Failed to validate server response")


def handle_error_response(response: requests.Response, error_mapping: Dict[int, str]) -> Tuple[bool, Dict[str, Any]]:
    """Handle error response enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate inputs
        if not isinstance(response, requests.Response):
            raise ValueError("Invalid response object")
        if not isinstance(error_mapping, dict):
            raise ValueError("Error mapping must be a dictionary")

        # Get response metadata
        status_code = response.status_code
        logger.info(f"Handling error response with status code {status_code}")

        # Extract error message
        error_msg = extract_error_message(response)
        if not error_msg:
            error_msg = error_mapping.get(status_code, "Unknown error occurred")

        # Log error details
        logger.error(f"API error response: {error_msg} (Status: {status_code})")

        return False, {"message": error_msg}

    except ValueError as e:
        logger.error(f"Error response handling validation error: {str(e)}")
        return False, {"message": "Invalid error response format"}
    except Exception as e:
        logger.error(f"Unexpected error handling error response: {str(e)}")
        return False, {"message": "Failed to process error response"}
