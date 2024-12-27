"""Input handling and validation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Union

from core.messaging.types import (
    ChannelIdentifier, ChannelType, Message,
    MessageRecipient, TextContent
)
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

# Constants
GREETING_KEYWORDS = {"hi", "hello", "hey", "start"}
BUTTON_ACTIONS = {"confirm_action"}


def get_action(message_body: str, message_type: str = "text", message: Dict[str, Any] = None) -> str:
    """Extract action from message

    Args:
        message_body: Raw message body text
        message_type: Type of message (text, interactive, etc)
        message: Full message data for interactive messages

    Returns:
        Extracted action string
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
        return message_body.strip().lower()

    except Exception:
        return ""


def extract_input_value(message_body: str, message_type: str = "text",
                        message: Dict[str, Any] = None) -> Union[str, Dict[str, Any]]:
    """Extract input value from message

    Args:
        message_body: Raw message body text
        message_type: Type of message (text, interactive, etc)
        message: Full message data for interactive messages

    Returns:
        Extracted input value
    """
    try:
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

        # Log input processing
        audit.log_flow_event(
            "bot_service",
            "input_processing",
            None,
            {"input": value, "type": message_type},
            "success"
        )

        return value

    except Exception:
        return ""


def is_greeting(text: str) -> bool:
    """Check if message is a greeting

    Args:
        text: Message text to check

    Returns:
        True if message is a greeting
    """
    return text.lower() in GREETING_KEYWORDS


def handle_invalid_input(state_manager: Any, flow_step_id: str = None) -> Message:
    """Handle invalid input with appropriate error message

    Args:
        state_manager: State manager instance
        flow_step_id: Optional flow step ID

    Returns:
        Error message response
    """
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id")
            },
            {"channel"}  # Only channel required
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Log invalid input
        audit.log_flow_event(
            "bot_service",
            "invalid_input",
            flow_step_id,
            {},
            "failure"
        )

        # Get required data
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

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
                member_id=member_id or "pending",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body=f"❌ {error_message}"
            )
        )

    except ValueError as e:
        logger.error(f"Failed to handle invalid input: {str(e)}")
        return Message(
            recipient=MessageRecipient(
                member_id="unknown",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body=f"❌ Critical Error: {str(e)}"
            )
        )
