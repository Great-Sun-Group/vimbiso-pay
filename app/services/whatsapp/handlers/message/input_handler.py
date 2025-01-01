"""Input handling and validation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Union

from core.config.config import GREETINGS
from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)

BUTTON_ACTIONS = {"confirm_action"}
MENU_ACTIONS = {
    "offer", "accept", "decline", "cancel",
    "start_registration", "upgrade_tier", "refresh"
}


def get_action(message_body: str, state_manager: Any = None, message_type: str = "text",
               message: Dict[str, Any] = None) -> str:
    """Extract action from message

    Args:
        message_body: Raw message body text
        state_manager: Optional state manager instance for flow state access
        message_type: Type of message (text, interactive, etc)
        message: Full message data for interactive messages

    Returns:
        Extracted action string or empty string for flow input
    """
    try:
        # Handle interactive messages
        if message_type == "interactive":
            interactive = message.get("interactive", {}) if message else {}
            interactive_type = interactive.get("type")

            # Check if we're in a flow first
            try:
                current_step = state_manager.get_current_step() if state_manager else None
                if current_step:
                    # In a flow - return empty string to let flow handler process it
                    flow_type = state_manager.get_flow_type()
                    logger.debug(f"In flow '{flow_type}' at step '{current_step}' - passing interactive input to flow")
                    return ""
            except Exception as e:
                error_context = ErrorContext(
                    error_type="state",
                    message="Failed to check flow state. Please try again",
                    details={
                        "message_type": message_type,
                        "error": str(e)
                    }
                )
                raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

            # Not in a flow - handle as menu action
            if interactive_type == "list_reply":
                return interactive.get("list_reply", {}).get("id", "").lower()
            elif interactive_type == "button_reply":
                return interactive.get("button_reply", {}).get("id", "").lower()
            return ""

        # Handle text messages
        text = str(message_body).strip().lower() if message_body else ""

        # Log the input for debugging
        logger.debug(f"Processing input text: '{text}'")
        logger.debug(f"Menu actions: {MENU_ACTIONS}")
        logger.debug(f"Is in menu actions: {text in MENU_ACTIONS}")

        # First check if it's a greeting (using GREETINGS from config)
        if text in GREETINGS:
            logger.info(f"Recognized greeting: {text}")
            return "hi"  # Normalize all greetings to "hi" action

        # Then check if it's a menu action
        if text in MENU_ACTIONS:
            logger.info(f"Recognized menu action: {text}")
            return text

        # Finally check if we're in an active flow
        try:
            current_step = state_manager.get_current_step() if state_manager else None
            if current_step:
                # In a flow - return empty string to let flow handler process it
                flow_type = state_manager.get_flow_type()
                logger.debug(f"In flow '{flow_type}' at step '{current_step}' - passing input to flow")
                return ""
        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to check flow state. Please try again",
                details={
                    "message_type": message_type,
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        # Not a greeting, flow input, or menu action - return empty string
        logger.debug(f"No action recognized for text: '{text}'")
        return ""

    except Exception as e:
        error_context = ErrorContext(
            error_type="input",
            message="Failed to process input. Please try again",
            details={
                "message_type": message_type,
                "message_body": message_body,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def extract_input_value(message_body: str, message_type: str = "text",
                        message: Dict[str, Any] = None,
                        state_manager: Any = None) -> Union[str, Dict[str, Any]]:
    """Extract input value from message

    Args:
        message_body: Raw message body text
        message_type: Type of message (text, interactive, etc)
        message: Full message data for interactive messages
        state_manager: Optional state manager instance for flow state access

    Returns:
        Extracted input value

    Raises:
        StateException: If input extraction fails
    """
    try:
        # Handle interactive messages
        if message_type == "interactive":
            interactive = message.get("interactive", {}) if message else {}
            interactive_type = interactive.get("type")

            # Check if we're in a flow first
            try:
                current_step = state_manager.get_current_step() if state_manager else None
                if current_step:
                    # In a flow - pass through the full interactive data
                    flow_type = state_manager.get_flow_type()
                    logger.debug(f"In flow '{flow_type}' at step '{current_step}' - passing interactive data")
                    return message.get("interactive", {})
            except Exception as e:
                error_context = ErrorContext(
                    error_type="state",
                    message="Failed to check flow state. Please try again",
                    details={
                        "message_type": message_type,
                        "error": str(e)
                    }
                )
                raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

            # Not in a flow - extract menu action
            if interactive_type == "list_reply":
                return interactive.get("list_reply", {}).get("id", "")
            elif interactive_type == "button_reply":
                return interactive.get("button_reply", {})

        # Handle text messages
        value = str(message_body).strip()

        # Log input processing
        logger.info(
            "Input processed successfully",
            extra={
                "message_type": message_type,
                "value_type": type(value).__name__
            }
        )

        return value

    except Exception as e:
        error_context = ErrorContext(
            error_type="input",
            message="Failed to extract input value. Please try again",
            details={
                "message_type": message_type,
                "message_body": message_body,
                "error": str(e)
            }
        )
        raise StateException(error_context.message)


def is_greeting(text: str) -> bool:
    """Check if message is a greeting using core config

    Args:
        text: Message text to check

    Returns:
        True if message is a greeting
    """
    return text.lower() in GREETINGS


def handle_invalid_input(state_manager: Any, flow_step_id: str = None) -> Message:
    """Handle invalid input with appropriate error message

    Args:
        state_manager: State manager instance
        flow_step_id: Optional flow step ID

    Returns:
        Error message response
    """
    try:
        # Get channel ID (StateManager validates)
        try:
            channel_id = state_manager.get_channel_id()
        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to get channel information. Please try again",
                step_id=flow_step_id,
                details={"error": str(e)}
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        # Log invalid input
        logger.warning(
            "Invalid input received",
            extra={
                "step_id": flow_step_id,
                "channel_id": channel_id
            }
        )

        # Create appropriate error context
        if flow_step_id == "amount":
            error_context = ErrorContext(
                error_type="input",
                message="Invalid amount format",
                step_id=flow_step_id,
                details={
                    "example": "100 USD, USD 100, ZWG 100, XAU 1",
                    "field": "amount"
                }
            )
        else:
            error_context = ErrorContext(
                error_type="input",
                message="Invalid input. Please try again with a valid option.",
                step_id=flow_step_id,
                details={"field": flow_step_id}
            )

        # Get error response through ErrorHandler
        error_response = ErrorHandler.handle_error(
            StateException(error_context.message),
            state_manager,
            error_context
        )

        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body=error_response['data']['action']['details']['message']
            )
        )

    except Exception as e:
        error_context = ErrorContext(
            error_type="input",
            message="Failed to handle invalid input. Please try again",
            step_id=flow_step_id,
            details={"error": str(e)}
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
