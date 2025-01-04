"""Base handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.utils.exceptions import ComponentException, SystemException
from core.utils.utils import wrap_text

from core.messaging.formatters import ErrorFormatters
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


def handle_default_action(state_manager: Any) -> WhatsAppMessage:
    """Handle default or unknown actions

    Args:
        state_manager: State manager instance for state access

    Returns:
        WhatsAppMessage: Error message for invalid actions
    """
    try:
        # Validate state manager
        if not state_manager:
            raise ComponentException(
                message="State manager is required",
                component="base_handler",
                field="state_manager",
                value="None"
            )

        # Get channel info through proper method
        channel_id = state_manager.get_channel_id()

        # Create error response
        return WhatsAppMessage.create_text(
            channel_id,
            wrap_text(ErrorFormatters.format_invalid_action(), channel_id)
        )

    except ComponentException as e:
        # Component errors become error messages
        logger.error(
            "Default action validation error",
            extra={"error": str(e)}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {str(e)}"
        )

    except Exception as e:
        # Wrap unexpected errors
        error = SystemException(
            message=str(e),
            code="DEFAULT_ACTION_ERROR",
            service="base_handler",
            action="handle_default"
        )
        logger.error(
            "Default action error",
            extra={"error": str(error)}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {str(error)}"
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
    """
    try:
        # Validate inputs
        if not state_manager:
            raise ComponentException(
                message="State manager is required",
                component="base_handler",
                field="state_manager",
                value="None"
            )

        if not message_text:
            raise ComponentException(
                message="Message text is required",
                component="base_handler",
                field="message_text",
                value="None"
            )

        # Get channel info through proper methods
        channel_id = state_manager.get_channel_id()

        # Create template response
        return WhatsAppMessage.create_text(channel_id, message_text)

    except ComponentException as e:
        # Component errors become error messages
        logger.error(
            "Response template validation error",
            extra={"error": str(e)}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {str(e)}"
        )

    except Exception as e:
        # Wrap unexpected errors
        error = SystemException(
            message=str(e),
            code="TEMPLATE_ERROR",
            service="base_handler",
            action="get_template",
            details={"message_text": message_text}
        )
        logger.error(
            "Response template error",
            extra={"error": str(error)}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {str(error)}"
        )


def format_error_response(state_manager: Any, error_message: str) -> WhatsAppMessage:
    """Format an error response message

    Args:
        state_manager: State manager instance for state access
        error_message: Error message to format

    Returns:
        WhatsAppMessage: Formatted error message
    """
    try:
        # Validate inputs
        if not state_manager:
            raise ComponentException(
                message="State manager is required",
                component="base_handler",
                field="state_manager",
                value="None"
            )

        if not error_message:
            error_message = "An unknown error occurred"

        # Get channel info through proper methods
        channel_id = state_manager.get_channel_id()

        # Create error response
        return WhatsAppMessage.create_text(
            channel_id,
            f"❌ {error_message}"
        )

    except ComponentException as e:
        # Component errors become error messages
        logger.error(
            "Error response validation error",
            extra={"error": str(e)}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {str(e)}"
        )

    except Exception as e:
        # Wrap unexpected errors
        error = SystemException(
            message=str(e),
            code="ERROR_FORMAT_ERROR",
            service="base_handler",
            action="format_error",
            details={"error_message": error_message}
        )
        logger.error(
            "Error response formatting failed",
            extra={"error": str(error)}
        )
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"❌ {str(error)}"
        )
