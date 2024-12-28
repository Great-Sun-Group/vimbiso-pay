"""Input handling and validation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Union

from core.config.config import GREETINGS
from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

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
        flow_data = state_manager.get("flow_data") if state_manager else None
        if flow_data and flow_data.get("current_step"):
            # In a flow - return empty string to let flow handler process it
            logger.debug(f"In flow '{flow_data.get('flow_type')}' at step '{flow_data.get('current_step')}' - passing input to flow")
            return ""

        # Not a greeting, flow input, or menu action - return empty string
        logger.debug(f"No action recognized for text: '{text}'")
        return ""

    except StateException as e:
        logger.error(f"Action extraction error: {str(e)}")
        raise  # Let caller handle error


def extract_input_value(message_body: str, message_type: str = "text",
                        message: Dict[str, Any] = None) -> Union[str, Dict[str, Any]]:
    """Extract input value from message

    Args:
        message_body: Raw message body text
        message_type: Type of message (text, interactive, etc)
        message: Full message data for interactive messages

    Returns:
        Extracted input value

    Raises:
        StateException: If input extraction fails
    """
    # Handle interactive messages
    if message_type == "interactive":
        interactive = message.get("interactive", {}) if message else {}
        interactive_type = interactive.get("type")

        if interactive_type == "list_reply":
            return interactive.get("list_reply", {}).get("id", "")
        elif interactive_type == "button_reply":
            return interactive.get("button_reply", {})

    # Handle text messages
    value = str(message_body).strip()

    # Log input processing (only log type)
    audit.log_flow_event(
        "bot_service",
        "input_processing",
        None,
        {"type": message_type},  # Only log message type
        "success"
    )

    return value


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
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")

        # Log invalid input (only log step)
        audit.log_flow_event(
            "bot_service",
            "invalid_input",
            flow_step_id,
            {"step": flow_step_id} if flow_step_id else {},  # Only log step if present
            "failure"
        )

        # Return appropriate error message
        error_message = (
            "Invalid amount format. Examples:\n"
            "100     (USD)\n"
            "USD 100\n"
            "ZWG 100\n"
            "XAU 1\n\n"
            "Please ensure you enter a valid number with an optional currency code."
        ) if flow_step_id == "amount" else "Invalid input. Please try again with a valid option."

        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body=f"❌ {error_message}"
            )
        )

    except StateException as e:
        logger.error(f"Failed to handle invalid input: {str(e)}")
        # Let caller handle error response
        raise
