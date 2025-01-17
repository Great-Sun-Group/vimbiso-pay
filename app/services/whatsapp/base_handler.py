"""WhatsApp message handler base implementation

This module provides base handlers for WhatsApp message formatting and error handling.
All state access is through the state manager which protects fields through schema
validation. Only component_data.data is unvalidated to give components freedom.
"""

import logging

from core.error.exceptions import ComponentException, SystemException
from core.error.types import INVALID_ACTION_MESSAGE
from core.state.interface import StateManagerInterface
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


def handle_default_action(channel_id: str = None, state_manager: StateManagerInterface = None) -> WhatsAppMessage:
    """Handle default or unknown actions

    Args:
        channel_id: Optional direct channel ID for stateless operation
        state_manager: Optional state manager for stateful operation

    Returns:
        WhatsAppMessage: Error message for invalid actions
    """
    try:
        # Get channel ID from either source
        if not channel_id and state_manager:
            channel_id = state_manager.get_channel_id()

        if not channel_id:
            channel_id = "unknown"  # Fallback for error messages

        # Create error response
        return WhatsAppMessage.create_text(
            channel_id,
            INVALID_ACTION_MESSAGE
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


def get_response_template(message_text: str, channel_id: str = None, state_manager: StateManagerInterface = None) -> WhatsAppMessage:
    """Get a basic WhatsApp message template

    Args:
        message_text: Text content for the message
        channel_id: Optional direct channel ID for stateless operation
        state_manager: Optional state manager for stateful operation

    Returns:
        WhatsAppMessage: Basic formatted WhatsApp message
    """
    try:
        # Validate message text
        if not message_text:
            raise ComponentException(
                message="Message text is required",
                component="base_handler",
                field="message_text",
                value="None"
            )

        # Get channel ID from either source
        if not channel_id and state_manager:
            channel_id = state_manager.get_channel_id()

        if not channel_id:
            raise ComponentException(
                message="Channel ID required from either state or direct input",
                component="base_handler",
                field="channel_id",
                value="None"
            )

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


def format_error_response(error_message: str, channel_id: str = None, state_manager: StateManagerInterface = None) -> WhatsAppMessage:
    """Format an error response message

    Args:
        error_message: Error message to format
        channel_id: Optional direct channel ID for stateless operation
        state_manager: Optional state manager for stateful operation

    Returns:
        WhatsAppMessage: Formatted error message
    """
    try:
        if not error_message:
            error_message = "An unknown error occurred"

        # Get channel ID from either source
        if not channel_id and state_manager:
            channel_id = state_manager.get_channel_id()

        if not channel_id:
            channel_id = "unknown"  # Fallback for error messages

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
