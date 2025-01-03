"""Input handling and validation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Union

from core.config.config import GREETINGS
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, SystemException

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

            # Check if we're in a flow
            current_step = state_manager.get_current_step() if state_manager else None
            if current_step:
                # In a flow - return empty string to let flow handler process it
                flow_type = state_manager.get_flow_type()
                logger.debug(f"In flow '{flow_type}' at step '{current_step}' - passing interactive input to flow")
                return ""

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

        # Check if we're in an active flow
        current_step = state_manager.get_current_step() if state_manager else None
        if current_step:
            # In a flow - return empty string to let flow handler process it
            flow_type = state_manager.get_flow_type()
            logger.debug(f"In flow '{flow_type}' at step '{current_step}' - passing input to flow")
            return ""

        # Not a greeting, flow input, or menu action - return empty string
        logger.debug(f"No action recognized for text: '{text}'")
        return ""

    except ComponentException as e:
        # Re-raise component errors with context
        logger.error("Input validation error", extra={
            "component": e.component,
            "field": e.field,
            "value": e.value
        })
        raise

    except Exception:
        # Handle system errors directly
        logger.error("Input processing error", extra={
            "message_body": message_body,
            "message_type": message_type,
            "current_step": state_manager.get_current_step() if state_manager else None
        })
        raise SystemException(
            message=ErrorHandler.MESSAGES["system"]["unknown_error"],
            code="INPUT_ERROR",
            service="input_handler",
            action="get_action"
        )


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
    """
    try:
        # Handle interactive messages
        if message_type == "interactive":
            interactive = message.get("interactive", {}) if message else {}
            interactive_type = interactive.get("type")

            # Check if we're in a flow
            current_step = state_manager.get_current_step() if state_manager else None
            if current_step:
                # In a flow - pass through the full interactive data
                flow_type = state_manager.get_flow_type()
                logger.debug(f"In flow '{flow_type}' at step '{current_step}' - passing interactive data")
                return message.get("interactive", {})

            # Not in a flow - extract menu action
            if interactive_type == "list_reply":
                return interactive.get("list_reply", {}).get("id", "")
            elif interactive_type == "button_reply":
                return interactive.get("button_reply", {})

            # Invalid interactive type
            raise ComponentException(
                message=f"Invalid interactive type: {interactive_type}",
                component="input_handler",
                field="interactive_type",
                value=str(interactive_type)
            )

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

    except ComponentException as e:
        # Re-raise component errors with context
        logger.error("Input validation error", extra={
            "component": e.component,
            "field": e.field,
            "value": e.value
        })
        raise

    except Exception:
        # Handle system errors directly
        logger.error("Input extraction error", extra={
            "message_body": message_body,
            "message_type": message_type,
            "interactive": message.get("interactive") if message else None
        })
        raise SystemException(
            message=ErrorHandler.MESSAGES["system"]["unknown_error"],
            code="INPUT_ERROR",
            service="input_handler",
            action="extract_value"
        )


def is_greeting(text: str) -> bool:
    """Check if message is a greeting using core config

    Args:
        text: Message text to check

    Returns:
        True if message is a greeting
    """
    return text.lower() in GREETINGS
