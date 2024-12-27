"""Base handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

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
    """
    try:
        if not state_manager:
            raise ValueError("State manager is required")

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            wrap_text(INVALID_ACTION, channel["identifier"])
        )
    except ValueError as e:
        logger.error(f"Failed to handle default action: {str(e)}")
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"Error: {str(e)}"
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
        if not state_manager:
            raise ValueError("State manager is required")
        if not message_text:
            raise ValueError("Message text is required")

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(channel["identifier"], message_text)

    except ValueError as e:
        logger.error(f"Failed to create response template: {str(e)}")
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"Error: {str(e)}"
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
        if not state_manager:
            raise ValueError("State manager is required")
        if not error_message:
            error_message = "An unknown error occurred"

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            f"❌ {error_message}"
        )

    except ValueError as e:
        logger.error(f"Failed to format error response: {str(e)}")
        return WhatsAppMessage.create_text(
            "unknown",  # Fallback identifier
            f"Critical Error: {str(e)}"
        )
