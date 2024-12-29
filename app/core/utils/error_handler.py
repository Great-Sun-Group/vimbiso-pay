import logging
from typing import Dict, Any, Optional, Tuple, Union

from core.messaging.types import (
    ChannelIdentifier, ChannelType,
    Message, MessageRecipient, TextContent
)
from .exceptions import (
    CredExCoreException as CredExBotException,
    InvalidInputException,
    APIException,
    StateException,
    ActionHandlerException,
    ConfigurationException,
)
from .flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def create_error_response(error_type: str, error_msg: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "data": {
            "action": {
                "type": "ERROR_VALIDATION",
                "details": {
                    "code": f"{error_type.upper()}_ERROR",
                    "message": error_msg
                }
            }
        }
    }


def update_error_state(state_manager: Any, error_type: str, error_msg: str, step_id: Optional[str] = None) -> None:
    """Update state with error information"""
    state_manager.update_state({
        "flow_data": {
            "flow_type": error_type,
            "step": 0,
            "current_step": "error",
            "data": {
                "error": error_msg,
                "error_type": error_type,
                "step": step_id
            }
        }
    })


def handle_error(e: Exception, bot_service: Any) -> Dict[str, Any]:
    """Centralized error handling function"""
    # Get error message based on type
    if isinstance(e, InvalidInputException):
        error_type = "input"
        message = "Sorry, I couldn't understand your input. Please try again."
    elif isinstance(e, APIException):
        error_type = "api"
        message = "We're experiencing some technical difficulties. Please try again later."
    elif isinstance(e, StateException):
        error_type = "state"
        message = "There was an issue with your current session. Please start over."
    elif isinstance(e, ActionHandlerException):
        error_type = "action"
        message = "I encountered an error while processing your request. Please try again."
    elif isinstance(e, ConfigurationException):
        error_type = "config"
        message = "There's a configuration issue on our end. Our team has been notified."
    elif isinstance(e, CredExBotException):
        error_type = "bot"
        message = "An unexpected error occurred. Please try again or contact support."
    else:
        error_type = "system"
        message = "I apologize, but something went wrong. Please try again later."

    try:
        # Update error state
        update_error_state(bot_service.user.state_manager, error_type, message)

        # Log error with context
        logger.error(
            f"Error: {type(e).__name__} - {str(e)}",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "state": bot_service.user.state_manager.get("flow_data")
            }
        )

        return create_error_response(error_type, message)

    except Exception as log_error:
        logger.error(f"Error during error handling: {str(log_error)}")
        return create_error_response("system", message)


def handle_api_error(e: Exception) -> Dict[str, Any]:
    """Handle API-specific errors and return appropriate response"""
    if isinstance(e, APIException):
        error_message = str(e)
    else:
        error_message = "An unexpected error occurred"
        logger.error(f"Unexpected error in API handler: {str(e)}")

    return create_error_response("api", error_message)


def handle_flow_error(
    state_manager: Any,
    error: Exception,
    flow_type: str = "auth",
    step_id: Optional[str] = None,
    return_message: bool = False
) -> Union[Tuple[bool, Dict[str, Any]], Message]:
    """Handle flow-related errors with state updates

    Args:
        state_manager: State manager instance
        error: Exception that occurred
        flow_type: Type of flow where error occurred
        step_id: Step where error occurred
        return_message: Whether to return Message object instead of tuple

    Returns:
        Either (success, error_response) tuple or Message object
    """
    error_msg = str(error)

    # Log error with context
    logger.error(
        f"Flow error in {step_id or 'unknown step'}: {error_msg}",
        extra={
            "error_type": type(error).__name__,
            "flow_type": flow_type,
            "step_id": step_id
        }
    )

    # Update error state
    update_error_state(state_manager, flow_type, error_msg, step_id)

    # Create standardized error response
    error_response = create_error_response(flow_type, error_msg)

    # Return Message if requested
    if return_message:
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=state_manager.get("channel")["identifier"]
                )
            ),
            content=TextContent(
                body=f"❌ Error: {error_msg}"
            ),
            metadata=error_response["data"]["action"]["details"]
        )

    # Return tuple otherwise
    return False, error_response


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
