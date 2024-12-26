import logging
from typing import Dict, Any, Optional
from .exceptions import (
    CredExCoreException as CredExBotException,
    InvalidInputException,
    APIException,
    StateException,
    ActionHandlerException,
    ConfigurationException,
)
from .utils import wrap_text
from .flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def handle_error(e: Exception, bot_service: Any) -> Dict[str, Any]:
    """Centralized error handling function"""
    if isinstance(e, InvalidInputException):
        message = "Sorry, I couldn't understand your input. Please try again."
    elif isinstance(e, APIException):
        message = (
            "We're experiencing some technical difficulties. Please try again later."
        )
    elif isinstance(e, StateException):
        message = "There was an issue with your current session. Please start over."
    elif isinstance(e, ActionHandlerException):
        message = (
            "I encountered an error while processing your request. Please try again."
        )
    elif isinstance(e, ConfigurationException):
        message = (
            "There's a configuration issue on our end. Our team has been notified."
        )
    elif isinstance(e, CredExBotException):
        message = "An unexpected error occurred. Please try again or contact support."
    else:
        message = "I apologize, but something went wrong. Please try again later."

    # Log error with context
    logger.error(
        f"Error: {type(e).__name__} - {str(e)}",
        extra={
            "error_type": type(e).__name__,
            "error_message": str(e),
            "mobile_number": bot_service.user.mobile_number,
            "state": getattr(bot_service.user.state, "state", {})
        }
    )

    return wrap_text(message, bot_service.user.mobile_number)


def handle_api_error(e: Exception) -> Dict[str, Any]:
    """Handle API-specific errors and return appropriate response"""
    if isinstance(e, APIException):
        error_message = str(e)
    else:
        error_message = "An unexpected error occurred"
        logger.error(f"Unexpected error in API handler: {str(e)}")

    return {
        "status": "error",
        "message": error_message
    }


def handle_flow_error(error: Exception, flow_id: Optional[str] = None, step_id: Optional[str] = None, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Handle flow-related errors with detailed context"""
    error_msg = str(error)
    error_type = type(error).__name__

    # Log error with context
    logger.error(
        f"Flow error in {step_id or 'unknown step'}: {error_msg}",
        extra={
            "flow_id": flow_id,
            "step_id": step_id,
            "error_type": error_type,
            "state": state
        }
    )

    # Log flow error event
    if flow_id:
        audit.log_flow_event(
            flow_id,
            "flow_error",
            step_id,
            {
                "error": error_msg,
                "error_type": error_type,
                "state": state
            },
            "failure"
        )

    # Determine user-friendly error message
    if isinstance(error, ValueError):
        # For validation errors, use the error message directly
        message = error_msg
    elif isinstance(error, StateException):
        message = "There was an issue with the flow state. Please try again."
    else:
        message = "An error occurred while processing your request. Please try again."

    return {
        "success": False,
        "message": message,
        "error": {
            "type": error_type,
            "message": error_msg,
            "step": step_id
        }
    }


def error_decorator(f):
    """Decorator to wrap functions with error handling"""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return handle_error(
                e, args[0]  # Assuming the first argument is always bot_service
            )
    return wrapper
