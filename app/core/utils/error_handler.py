"""Centralized error handling through state management

This module provides the ONLY error handling for the entire system.
All components should let errors propagate up to be handled here.

Error Types:
- flow: Flow-specific errors (step validation, routing)
- state: State validation errors (structure, access)
- input: User input validation errors
- api: External API errors
- system: Internal system errors

Error Context Requirements:
- error_type: Type of error (required)
- message: Clear user-facing message (required)
- step_id: For flow errors (optional)
- details: Relevant context (optional)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)

logger = logging.getLogger(__name__)


@dataclass
class ErrorContext:
    """Error context for state updates

    Required for ALL errors to ensure consistent handling.
    Components should NOT create error messages directly.

    Fields:
        error_type: Type of error (flow, state, input, api, system)
        message: Clear user-facing message
        step_id: Only required for flow errors, should be None for other types
        details: Additional context (optional)

    Note:
        step_id is ONLY required when error_type is "flow"
        For all other error types, step_id should be None
    """
    error_type: str
    message: str
    step_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate error context requirements"""
        if self.error_type == "flow" and not self.step_id:
            raise ValueError("step_id is required for flow errors")
        if self.error_type != "flow" and self.step_id:
            raise ValueError("step_id should only be set for flow errors")


class ErrorHandler:
    """Centralized error handling through state management

    This is the ONLY place errors should be handled.
    Components should:
    1. Update state to trigger validation
    2. Let errors propagate up
    3. NOT catch or handle errors
    4. NOT create error messages
    """

    # Standard error messages - Components should NOT create messages
    ERROR_MESSAGES = {
        "flow": {
            "validation": "Invalid input for this step. Please try again.",
            "routing": "Unable to process that action right now. Please try again.",
            "state": "Flow state is invalid. Please start over.",
            "generic": "An error occurred in the current flow. Please try again."
        },
        "state": {
            "validation": "Invalid state structure detected.",
            "access": "Unable to access required state data.",
            "update": "Failed to update state properly.",
            "generic": "There was an issue with your current session. Please start over."
        },
        "input": {
            "format": "Input format is invalid. Please check and try again.",
            "validation": "Input validation failed. Please try again.",
            "missing": "Required input is missing. Please provide all required information.",
            "generic": "Sorry, I couldn't understand your input. Please try again."
        },
        "api": {
            "connection": "Unable to connect to external service.",
            "response": "Received invalid response from external service.",
            "timeout": "Request timed out. Please try again.",
            "generic": "We're experiencing some technical difficulties. Please try again later."
        },
        "system": {
            "config": "System configuration error detected.",
            "runtime": "Unexpected runtime error occurred.",
            "resource": "Required system resource unavailable.",
            "generic": "I apologize, but something went wrong. Please try again later."
        }
    }

    @classmethod
    def get_error_context(cls, error: Exception, step_id: Optional[str] = None) -> ErrorContext:
        """Map exception to error context with detailed messages

        Args:
            error: The exception to handle
            step_id: Step ID (required for flow errors, should be None otherwise)

        Returns:
            ErrorContext with appropriate error details

        Note:
            step_id is only used when the error maps to a flow error
            For other error types, step_id is ignored
        """
        from .exceptions import (APIException, ConfigurationException,
                                 FlowException, InvalidInputException,
                                 StateException)

        # Map error to type and subtype
        if isinstance(error, FlowException):
            # Flow errors require step_id
            if not step_id:
                raise ValueError("step_id is required for flow errors")
            error_type = "flow"
            subtype = error.subtype if hasattr(error, 'subtype') else "generic"
            # Build flow error context with required step_id
            return ErrorContext(
                error_type=error_type,
                message=cls.ERROR_MESSAGES[error_type][subtype],
                step_id=step_id,  # Required for flow
                details={
                    "error_class": error.__class__.__name__,
                    "error_message": str(error),
                    "subtype": subtype
                }
            )

        # Handle non-flow errors (step_id should be None)
        if isinstance(error, InvalidInputException):
            error_type = "input"
            subtype = error.subtype if hasattr(error, 'subtype') else "generic"
        elif isinstance(error, APIException):
            error_type = "api"
            subtype = error.subtype if hasattr(error, 'subtype') else "generic"
        elif isinstance(error, StateException):
            error_type = "state"
            subtype = error.subtype if hasattr(error, 'subtype') else "generic"
        elif isinstance(error, ConfigurationException):
            error_type = "system"
            subtype = "config"
        else:
            error_type = "system"
            subtype = "runtime"

        # Build non-flow error context (no step_id)
        return ErrorContext(
            error_type=error_type,
            message=cls.ERROR_MESSAGES[error_type][subtype],
            step_id=None,  # Not used for non-flow errors
            details={
                "error_class": error.__class__.__name__,
                "error_message": str(error),
                "subtype": subtype
            }
        )

    @classmethod
    def create_error_response(cls, context: ErrorContext) -> Dict[str, Any]:
        """Create standardized error response with full context

        Components should NOT create error responses directly.
        All error responses should come through here.

        Note:
            step_id is only included for flow errors
            Other error types will not include step_id
        """
        # Build base response
        response = {
            "data": {
                "action": {
                    "type": "ERROR",
                    "details": {
                        "code": f"{context.error_type.upper()}_ERROR",
                        "message": context.message,
                        "error_type": context.error_type
                    }
                }
            }
        }

        # Add step_id only for flow errors
        if context.error_type == "flow":
            # step_id is required for flow errors (validated in ErrorContext)
            response["data"]["action"]["details"]["step_id"] = context.step_id

        # Add any additional context
        if context.details:
            response["data"]["action"]["details"].update(context.details)

        return response

    @classmethod
    def update_error_state(cls, state_manager: Any, context: ErrorContext) -> None:
        """Update state with standardized error information

        Components should NOT update error state directly.
        All error state updates should come through here.
        """
        # Build standardized error state
        error_state = {
            "flow_data": {
                "flow_type": context.error_type,
                "step": 0,  # Reset step on error
                "current_step": "error",
                "data": {
                    "error": {
                        "type": context.error_type,
                        "message": context.message,
                        "timestamp": state_manager.get_timestamp()
                    }
                }
            }
        }

        # Add step info for flow errors
        if context.step_id:
            error_state["flow_data"]["data"]["error"]["step_id"] = context.step_id

        # Add any additional context
        if context.details:
            error_state["flow_data"]["data"]["error"]["details"] = context.details

        # Let StateManager validate error state structure
        state_manager.update_state(error_state)

    @classmethod
    def handle_error(cls, error: Exception, state_manager: Any, step_id: Optional[str] = None) -> Dict[str, Any]:
        """Central error handling through state management

        This is the ONLY place errors should be handled.
        Components should let errors propagate up to here.
        """
        try:
            # Get standardized error context
            context = cls.get_error_context(error, step_id)

            # Update error state through StateManager
            cls.update_error_state(state_manager, context)

            # Log error with full context
            logger.error(
                f"Error handled: {context.error_type}",
                extra={
                    "error_type": context.error_type,
                    "error_class": error.__class__.__name__,
                    "error_message": str(error),
                    "step_id": step_id,
                    "state": state_manager.get("flow_data"),
                    "details": context.details
                }
            )

            # Return standardized error response
            return cls.create_error_response(context)

        except Exception as e:
            # Log error handling failure
            logger.error(
                "Error during error handling",
                extra={
                    "handler_error": str(e),
                    "original_error": str(error),
                    "error_class": error.__class__.__name__
                }
            )

            # Return system error response
            return cls.create_error_response(
                ErrorContext(
                    "system",
                    cls.ERROR_MESSAGES["system"]["generic"],
                    details={"handler_error": str(e)}
                )
            )

    @classmethod
    def handle_flow_error(
        cls,
        state_manager: Any,
        error: Exception,
        step_id: Optional[str] = None,
        return_message: bool = False
    ) -> Union[Tuple[bool, Dict[str, Any]], Message]:
        """Handle flow-specific errors through state management

        Special handling for flow errors to support message responses.
        Components should still let errors propagate up.
        """
        try:
            # Get flow-specific error context
            context = cls.get_error_context(error, step_id)
            if context.error_type != "flow":
                context.error_type = "flow"
                context.message = cls.ERROR_MESSAGES["flow"]["generic"]

            # Update error state
            cls.update_error_state(state_manager, context)

            # Log flow error with full context
            logger.error(
                f"Flow error in step {step_id or 'unknown'}",
                extra={
                    "error_type": "flow",
                    "error_class": error.__class__.__name__,
                    "error_message": str(error),
                    "step_id": step_id,
                    "state": state_manager.get("flow_data"),
                    "details": context.details
                }
            )

            # Create error response
            error_response = cls.create_error_response(context)

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
                        body=f"❌ {context.message}"
                    ),
                    metadata=error_response["data"]["action"]["details"]
                )

            # Return tuple otherwise
            return False, error_response

        except Exception as e:
            # Log error handling failure
            logger.error(
                "Error during flow error handling",
                extra={
                    "handler_error": str(e),
                    "original_error": str(error),
                    "step_id": step_id
                }
            )

            # Return system error response
            context = ErrorContext(
                "system",
                cls.ERROR_MESSAGES["system"]["generic"],
                details={"handler_error": str(e)}
            )

            if return_message:
                return Message(
                    recipient=MessageRecipient(
                        channel_id=ChannelIdentifier(
                            channel=ChannelType.WHATSAPP,
                            value=state_manager.get("channel")["identifier"]
                        )
                    ),
                    content=TextContent(
                        body=f"❌ {context.message}"
                    ),
                    metadata={"error": "system_error"}
                )

            return False, cls.create_error_response(context)


def error_decorator(f):
    """Decorator for standardized error handling through state

    Components should use this decorator to:
    1. Let errors propagate up
    2. Get handled by ErrorHandler
    3. Return standardized responses
    """
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Get state manager from arguments
            state_manager = None

            # Try service instance
            if args and hasattr(args[0], "state_manager"):
                state_manager = args[0].state_manager

            # Try user object
            if not state_manager and args and hasattr(args[0], "user"):
                user = args[0].user
                if hasattr(user, "state_manager"):
                    state_manager = user.state_manager

            # Handle missing state manager
            if not state_manager:
                logger.error(
                    "Missing state manager in error decorator",
                    extra={
                        "function": f.__name__,
                        "error": str(e),
                        "args": str(args)
                    }
                )
                return ErrorHandler.create_error_response(
                    ErrorContext(
                        "system",
                        cls.ERROR_MESSAGES["system"]["generic"],
                        details={"missing_state_manager": True}
                    )
                )

            # Get step_id if available
            step_id = kwargs.get("step_id")
            if not step_id and args:
                step_id = getattr(args[0], "step_id", None)

            # Handle error through ErrorHandler
            return ErrorHandler.handle_error(e, state_manager, step_id)

    return wrapper
