"""Base handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
from core.utils.state_validator import StateValidator
from core.utils.utils import wrap_text

from .screens import INVALID_ACTION
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


def handle_default_action(state_manager: Any) -> WhatsAppMessage:
    """Handle default or unknown actions

    Args:
        state_manager: State manager instance for state access

    Returns:
        WhatsAppMessage: Error message for invalid actions

    Raises:
        StateException: If state validation fails
    """
    try:
        if not state_manager:
            error_context = ErrorContext(
                error_type="state",
                message="State manager is required",
                details={"state_manager": None}
            )
            raise StateException(ErrorHandler.handle_error(
                StateException("Missing state manager"),
                None,
                error_context
            ))

        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {"channel": state_manager.get("channel")},
                {"channel"}
            )
            if not validation.is_valid:
                error_context = ErrorContext(
                    error_type="state",
                    message="Invalid state for default action",
                    details={"error": validation.error_message}
                )
                raise StateException(ErrorHandler.handle_error(
                    StateException(validation.error_message),
                    state_manager,
                    error_context
                ))

            channel = state_manager.get("channel")
            return WhatsAppMessage.create_text(
                channel["identifier"],
                wrap_text(INVALID_ACTION, channel["identifier"])
            )

        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to validate state",
                details={"error": str(e)}
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",
            message="Failed to handle default action",
            details={"error": str(e)}
        )
        logger.error(
            "Default action error",
            extra={"error_context": error_context.__dict__}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {error_context.message}"
        )


def format_synopsis(synopsis: str, style: str = None) -> str:
    """Format text synopsis with line breaks for better readability

    Args:
        synopsis: Text to format
        style: Optional style to apply to each word (e.g. '*' for bold)

    Returns:
        str: Formatted text with appropriate line breaks
    """
    if not synopsis:
        return ""

    formatted_synopsis = ""
    words = synopsis.split()
    line_length = 0

    for word in words:
        # If adding the word exceeds the line length, start a new line
        if line_length + len(word) + 1 > 35:
            formatted_synopsis += "\n"
            line_length = 0
        if style:
            word = f"{style}{word}{style}"
        formatted_synopsis += word + " "
        line_length += len(word) + 1

    return formatted_synopsis.strip()


def get_response_template(state_manager: Any, message_text: str) -> WhatsAppMessage:
    """Get a basic WhatsApp message template

    Args:
        state_manager: State manager instance for state access
        message_text: Text content for the message

    Returns:
        WhatsAppMessage: Basic formatted WhatsApp message

    Raises:
        StateException: If state validation fails
    """
    try:
        # Validate inputs
        if not state_manager:
            error_context = ErrorContext(
                error_type="state",
                message="State manager is required",
                details={"state_manager": None}
            )
            raise StateException(error_context.message)

        if not message_text:
            error_context = ErrorContext(
                error_type="input",
                message="Message text is required",
                details={"message_text": None}
            )
            raise StateException(error_context.message)

        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {"channel": state_manager.get("channel")},
                {"channel"}
            )
            if not validation.is_valid:
                error_context = ErrorContext(
                    error_type="state",
                    message="Invalid state for message template",
                    details={"error": validation.error_message}
                )
                raise StateException(ErrorHandler.handle_error(
                    StateException(validation.error_message),
                    state_manager,
                    error_context
                ))

            channel = state_manager.get("channel")
            return WhatsAppMessage.create_text(channel["identifier"], message_text)

        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to validate state",
                details={"error": str(e)}
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",
            message="Failed to create response template",
            details={
                "message_text": message_text,
                "error": str(e)
            }
        )
        logger.error(
            "Response template error",
            extra={"error_context": error_context.__dict__}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {error_context.message}"
        )


def format_error_response(state_manager: Any, error_message: str) -> WhatsAppMessage:
    """Format an error response message

    Args:
        state_manager: State manager instance for state access
        error_message: Error message to format

    Returns:
        WhatsAppMessage: Formatted error message

    Raises:
        StateException: If state validation fails
    """
    try:
        # Validate inputs
        if not state_manager:
            error_context = ErrorContext(
                error_type="state",
                message="State manager is required",
                details={"state_manager": None}
            )
            raise StateException(error_context.message)

        if not error_message:
            error_message = "An unknown error occurred"

        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {"channel": state_manager.get("channel")},
                {"channel"}
            )
            if not validation.is_valid:
                error_context = ErrorContext(
                    error_type="state",
                    message="Invalid state for error response",
                    details={"error": validation.error_message}
                )
                raise StateException(ErrorHandler.handle_error(
                    StateException(validation.error_message),
                    state_manager,
                    error_context
                ))

            channel = state_manager.get("channel")
            return WhatsAppMessage.create_text(
                channel["identifier"],
                f"❌ {error_message}"
            )

        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to validate state",
                details={"error": str(e)}
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",
            message="Failed to format error response",
            details={
                "error_message": error_message,
                "error": str(e)
            }
        )
        logger.error(
            "Error response formatting failed",
            extra={"error_context": error_context.__dict__}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {error_context.message}"
        )
