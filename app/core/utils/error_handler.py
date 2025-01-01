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
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

from rest_framework import status
from rest_framework.response import Response

from core.config.state_manager import StateManager
from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.error_types import ErrorContext

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling through state management

    This is the ONLY place errors should be handled.
    Components should:
    1. Update state to trigger validation
    2. Let errors propagate up
    3. NOT catch or handle errors
    4. NOT create error messages
    """

    # Standard error messages with placeholders - Components should NOT create messages
    ERROR_MESSAGES = {
        "flow": {
            "validation": "The {field} you entered is not valid. Please check and try again.",
            "routing": "Cannot process {action} at this time. Please try again.",
            "state": "There was a problem with your current step. Please start over.",
            "generic": "An error occurred while processing your request. Please try again."
        },
        "state": {
            "validation": "The system detected an invalid state. Please start over.",
            "access": "Unable to access your current session data. Please try again.",
            "update": "Failed to save your progress. Please try again.",
            "generic": "There was a problem with your session. Please start over."
        },
        "input": {
            "format": "The format of {field} is incorrect. Example: {example}",
            "validation": "The {field} you provided is not valid. {reason}",
            "missing": "Please provide {field}.",
            "generic": "I couldn't understand your input. Please try again."
        },
        "api": {
            "connection": "Unable to connect to our services. Please try again in a moment.",
            "response": "We received an unexpected response. Please try again.",
            "timeout": "The request took too long. Please try again.",
            "generic": "We're having technical difficulties. Please try again shortly."
        },
        "system": {
            "config": "There's a configuration issue. Our team has been notified.",
            "runtime": "An unexpected error occurred. Our team has been notified.",
            "resource": "A required service is unavailable. Please try again shortly.",
            "generic": "Something went wrong on our end. Please try again later."
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
                                 InvalidInputException, StateException)

        # Map exception types to error types
        # Determine error type from exception
        if step_id:
            # If step_id is provided, this is a flow error
            error_type = "flow"
            subtype = "generic"
        elif isinstance(error, InvalidInputException):
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

    # Standard message prefixes
    ERROR_PREFIX = "❌"
    SUCCESS_PREFIX = "✅"
    MENU_PREFIX = "🏡"

    @classmethod
    def format_error_message(cls, message: str) -> str:
        """Format error message with standard prefix"""
        return f"{cls.ERROR_PREFIX} {message}"

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
                        "message": cls.format_error_message(context.message),
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
                        "timestamp": datetime.utcnow().isoformat()
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
    def handle_error(cls, error: Exception, state_manager: Any, error_context: Optional[Union[ErrorContext, str]] = None) -> Dict[str, Any]:
        """Central error handling through state management

        This is the ONLY place errors should be handled.
        Components should let errors propagate up to here.

        Args:
            error: The exception to handle
            state_manager: State manager instance
            error_context: Either ErrorContext object or step_id string
        """
        try:
            # Get standardized error context
            if isinstance(error_context, ErrorContext):
                context = error_context
            else:
                context = cls.get_error_context(error, error_context)  # error_context is step_id string

            # Update error state through StateManager
            cls.update_error_state(state_manager, context)

            # Log error with full context
            logger.error(
                f"Error handled: {context.error_type}",
                extra={
                    "error_type": context.error_type,
                    "error_class": error.__class__.__name__,
                    "error_message": str(error),
                    "step_id": context.step_id,
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
        error_context: Optional[Union[ErrorContext, str]] = None,
        return_message: bool = False
    ) -> Union[Tuple[bool, Dict[str, Any]], Message]:
        """Handle flow-specific errors through state management

        Special handling for flow errors to support message responses.
        Components should still let errors propagate up.

        Args:
            state_manager: State manager instance
            error: The exception to handle
            error_context: Either ErrorContext object or step_id string
            return_message: Whether to return Message object
        """
        try:
            # Get flow-specific error context
            if isinstance(error_context, ErrorContext):
                context = error_context
            else:
                context = cls.get_error_context(error, error_context)  # error_context is step_id string
                if context.error_type != "flow":
                    context.error_type = "flow"
                    context.message = cls.ERROR_MESSAGES["flow"]["generic"]

            # Update error state
            cls.update_error_state(state_manager, context)

            # Log flow error with full context
            logger.error(
                f"Flow error in step {context.step_id or 'unknown'}",
                extra={
                    "error_type": "flow",
                    "error_class": error.__class__.__name__,
                    "error_message": str(error),
                    "step_id": context.step_id,
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
                        body=cls.format_error_message(context.message)
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
                    "step_id": context.step_id
                }
            )

            # Create system error context
            system_context = ErrorContext(
                "system",
                cls.ERROR_MESSAGES["system"]["generic"],
                details={
                    "flow_type": "offer",
                    "error": str(e)
                }
            )

            try:
                # Update error state
                cls.update_error_state(state_manager, system_context)

                if return_message:
                    return Message(
                        recipient=MessageRecipient(
                            channel_id=ChannelIdentifier(
                                channel=ChannelType.WHATSAPP,
                                value=state_manager.get("channel")["identifier"]
                            )
                        ),
                        content=TextContent(
                            body=cls.format_error_message("Unable to start flow. Please try again")
                        ),
                        metadata={"error": "system_error"}
                    )

                return False, cls.create_error_response(system_context)

            except Exception:
                # Last resort - return basic error message when state update fails
                if return_message:
                    return Message(
                        recipient=MessageRecipient(
                            channel_id=ChannelIdentifier(
                                channel=ChannelType.WHATSAPP,
                                value=state_manager.get("channel")["identifier"]
                            )
                        ),
                        content=TextContent(
                            body=cls.format_error_message("❌ Unable to start flow. Please try again")
                        )
                    )

                return False, {
                    "data": {
                        "action": {
                            "type": "ERROR",
                            "details": {
                                "message": "Unable to start flow. Please try again"
                            }
                        }
                    }
                }


def handle_api_error(error: Exception) -> Response:
    """Handle API errors consistently returning REST framework Response

    Args:
        error: The exception to handle

    Returns:
        Response: Django REST framework response with error details
    """
    # Get error context
    error_context = ErrorHandler.get_error_context(error)
    error_response = ErrorHandler.create_error_response(error_context)

    # Map error types to status codes
    status_codes = {
        'input': status.HTTP_400_BAD_REQUEST,
        'api': status.HTTP_502_BAD_GATEWAY,
        'state': status.HTTP_409_CONFLICT,
        'flow': status.HTTP_400_BAD_REQUEST,
        'system': status.HTTP_500_INTERNAL_SERVER_ERROR
    }

    return Response(
        error_response,
        status=status_codes.get(error_context.error_type, status.HTTP_500_INTERNAL_SERVER_ERROR)
    )


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

            # Get state_manager - either passed directly or through service instance
            if args and isinstance(args[0], StateManager):
                state_manager = args[0]
            elif args and hasattr(args[0], "state_manager"):
                state_manager = args[0].state_manager

            # Handle missing state manager
            if not state_manager:
                logger.error(
                    "Missing state manager in error decorator",
                    extra={
                        "function": f.__name__,
                        "error": str(e),
                        "func_args": str(args)
                    }
                )
                return ErrorHandler.create_error_response(
                    ErrorContext(
                        "system",
                        ErrorHandler.ERROR_MESSAGES["system"]["generic"],
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
