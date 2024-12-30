"""Base CredEx functionality using pure functions"""
import logging
import sys
from typing import Any, Dict, Optional, Tuple

import requests
from core.transactions.exceptions import TransactionError
from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException

# Configure logging to output to stdout with DEBUG level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def extract_error_message(response: requests.Response) -> Tuple[str, Dict[str, Any]]:
    """Extract the most user-friendly error message from a response

    Args:
        response: Response object from API request

    Returns:
        Tuple of (error message, error details)

    Raises:
        StateException: If error message extraction fails
    """
    try:
        # Try to parse response as JSON
        try:
            error_data = response.json()
            logger.debug(f"Response content: {error_data}")
        except Exception:
            logger.debug(f"Non-JSON response: {response.text}")
            error_data = {}

        error_details = {
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type"),
            "error_data": error_data
        }

        # Direct message in response
        if error_data.get("message"):
            return error_data["message"], error_details

        # Check for business logic errors in action.details
        action = error_data.get("data", {}).get("action", {})
        if action.get("type") == "CREDEX_CREATE_FAILED":
            details = action.get("details", {})
            if details.get("reason"):
                error_details["action"] = action
                return details["reason"], error_details

        # Check for error details
        if error_data.get("error"):
            return error_data["error"], error_details

        # Check for specific error conditions
        if "Required field missing" in str(error_data):
            return "Please check your input and try again.", error_details
        elif response.status_code == 404:
            # Check if this is a member not found case
            if "Member not found" in str(error_data):
                return "Member not found", error_details
            return "Recipient account not found. Please check the handle and try again.", error_details
        elif response.status_code == 403:
            return "You don't have permission to perform this action.", error_details
        elif response.status_code == 502:
            return "The service is temporarily unavailable. Please try again in a few minutes.", error_details
        elif response.status_code >= 500:
            return "The service is experiencing technical difficulties. Please try again later.", error_details

        # Last resort - return raw response content if nothing else found
        if error_data:
            return str(error_data), error_details

        return f"Server error {response.status_code}. Please try again.", error_details

    except Exception as e:
        error_context = ErrorContext(
            error_type="api",
            message="Failed to extract error message from response",
            details={
                "status_code": response.status_code,
                "error": str(e)
            }
        )
        logger.error(
            "Error message extraction failed",
            extra={"error_context": error_context.__dict__}
        )
        raise StateException(error_context.message)


def make_credex_request(
    group: str,
    action: str,
    method: str = "POST",
    payload: Optional[Dict[str, Any]] = None,
    jwt_token: Optional[str] = None,
) -> requests.Response:
    """Make an HTTP request to the CredEx API using endpoint groups"""
    from .config import CredExConfig, CredExEndpoints

    try:
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
            if response.status_code >= 400:
                error_msg, error_details = extract_error_message(response)
                error_context = ErrorContext(
                    error_type="api",
                    message=error_msg,
                    details={
                        "group": group,
                        "action": action,
                        "method": method,
                        **error_details
                    }
                )
                raise TransactionError(ErrorHandler.handle_error(
                    StateException(error_msg),
                    None,
                    error_context
                ))

            # Log successful response for debugging
            try:
                logger.debug(f"Success response content: {response.json()}")
            except Exception:
                logger.debug(f"Non-JSON success response: {response.text}")

            return response

        except requests.exceptions.RequestException as e:
            error_context = ErrorContext(
                error_type="api",
                message="Network error occurred",
                details={
                    "group": group,
                    "action": action,
                    "method": method,
                    "error": str(e)
                }
            )
            raise TransactionError(ErrorHandler.handle_error(
                StateException("Network error"),
                None,
                error_context
            ))

    except Exception as e:
        error_context = ErrorContext(
            error_type="api",
            message="Failed to make API request",
            details={
                "group": group,
                "action": action,
                "method": method,
                "error": str(e)
            }
        )
        raise TransactionError(ErrorHandler.handle_error(
            StateException("API request failed"),
            None,
            error_context
        ))


def validate_response(
    response: requests.Response,
    error_mapping: Optional[Dict[int, str]] = None
) -> Dict[str, Any]:
    """Validate API response enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate input
        if not isinstance(response, requests.Response):
            error_context = ErrorContext(
                error_type="api",
                message="Invalid response object",
                details={"type": type(response).__name__}
            )
            raise StateException(error_context.message)

        # Get response metadata
        content_type = response.headers.get("Content-Type", "")
        status_code = response.status_code

        logger.info(f"Validating API response with status code {status_code}")
        logger.debug(f"Content-Type: {content_type}")
        logger.debug(f"Response text: {response.text}")

        # Validate content type
        if "application/json" not in content_type.lower():
            error_context = ErrorContext(
                error_type="api",
                message="Invalid response format from server",
                details={
                    "content_type": content_type,
                    "status_code": status_code
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException("Invalid content type"),
                None,
                error_context
            ))

        # Parse response data
        try:
            data = response.json()
            if not isinstance(data, dict):
                error_context = ErrorContext(
                    error_type="api",
                    message="Invalid response format from server",
                    details={
                        "data_type": type(data).__name__,
                        "status_code": status_code
                    }
                )
                raise StateException(ErrorHandler.handle_error(
                    StateException("Invalid response data"),
                    None,
                    error_context
                ))
            logger.debug(f"Parsed JSON response: {data}")
        except ValueError as err:
            error_context = ErrorContext(
                error_type="api",
                message="Invalid response format from server",
                details={
                    "error": str(err),
                    "status_code": status_code
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException("JSON parse error"),
                None,
                error_context
            ))

        # Handle error responses
        if status_code >= 400:
            error_msg = error_mapping.get(status_code) if error_mapping else None
            if not error_msg:
                error_msg, error_details = extract_error_message(response)
            error_context = ErrorContext(
                error_type="api",
                message=error_msg,
                details={
                    "status_code": status_code,
                    **(error_details if 'error_details' in locals() else {})
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException(error_msg),
                None,
                error_context
            ))

        return data

    except StateException:
        raise
    except Exception as e:
        error_context = ErrorContext(
            error_type="api",
            message="Failed to validate server response",
            details={"error": str(e)}
        )
        raise StateException(ErrorHandler.handle_error(e, None, error_context))


def handle_error_response(response: requests.Response, error_mapping: Dict[int, str]) -> Tuple[bool, Dict[str, Any]]:
    """Handle error response enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate inputs
        if not isinstance(response, requests.Response):
            error_context = ErrorContext(
                error_type="api",
                message="Invalid response object",
                details={"type": type(response).__name__}
            )
            raise StateException(error_context.message)

        if not isinstance(error_mapping, dict):
            error_context = ErrorContext(
                error_type="api",
                message="Invalid error mapping",
                details={"type": type(error_mapping).__name__}
            )
            raise StateException(error_context.message)

        # Get response metadata
        status_code = response.status_code
        logger.info(f"Handling error response with status code {status_code}")

        # Extract error message
        error_msg, error_details = extract_error_message(response)
        if not error_msg:
            error_msg = error_mapping.get(status_code, "Unknown error occurred")

        # Create error context
        error_context = ErrorContext(
            error_type="api",
            message=error_msg,
            details={
                "status_code": status_code,
                **error_details
            }
        )

        # Log error details
        logger.error(
            "API error response",
            extra={
                "error_context": error_context.__dict__
            }
        )

        return False, {
            "message": error_msg,
            "details": error_context.details
        }

    except Exception as e:
        error_context = ErrorContext(
            error_type="api",
            message="Failed to process error response",
            details={"error": str(e)}
        )
        logger.error(
            "Error response handling failed",
            extra={"error_context": error_context.__dict__}
        )
        return False, {
            "message": error_context.message,
            "details": error_context.details
        }
