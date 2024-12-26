"""Input handling and validation for WhatsApp messages"""
import logging
from typing import Any, Dict, Union

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class InputHandler:
    """Handles message input processing and validation"""

    GREETING_KEYWORDS = {"hi", "hello", "hey", "start"}
    BUTTON_ACTIONS = {"confirm_action"}

    def __init__(self, service: Any):
        self.service = service

    def get_action(self) -> str:
        """Extract action from message"""
        try:
            # Handle interactive messages
            if self.service.message_type == "interactive":
                interactive = self.service.message.get("interactive", {})
                interactive_type = interactive.get("type")

                # Log interactive type at INFO level
                logger.info(f"Interactive type: {interactive_type}")

                if interactive_type == "list_reply":
                    action = interactive.get("list_reply", {}).get("id", "").lower()
                    logger.debug(f"List reply action: {action}")
                elif interactive_type == "button_reply":
                    action = interactive.get("button_reply", {}).get("id", "").lower()
                    logger.debug(f"Button reply action: {action}")
                else:
                    action = ""
            else:
                # For text messages
                action = self.service.body.strip().lower()
                logger.debug(f"Text message action: {action}")

            logger.info(f"Extracted action: {action}")
            return action

        except Exception as e:
            logger.error(f"Error extracting action: {str(e)}")
            # Get member ID and channel identifier
            current_state = self.service.user.state.state or {}
            member_id = current_state.get("member_id", "pending")
            channel_id = self.service.user.channel_identifier

            # Log error with member and channel context
            audit.log_flow_event(
                "bot_service",
                "action_extraction_error",
                None,
                {
                    "error": str(e),
                    "member_id": member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id
                    }
                },
                "failure"
            )
            return ""

    def extract_input_value(self) -> Union[str, Dict[str, Any]]:
        """Extract input value from message"""
        try:
            # Handle interactive messages
            if self.service.message_type == "interactive":
                interactive = self.service.message.get("interactive", {})
                interactive_type = interactive.get("type")

                logger.info(f"Extracting input from interactive type: {interactive_type}")

                if interactive_type == "list_reply":
                    value = interactive.get("list_reply", {}).get("id")
                    logger.debug(f"List reply value: {value}")
                    return value
                elif interactive_type == "button_reply":
                    value = interactive.get("button_reply", {})
                    logger.debug(f"Button reply value: {value}")
                    return value

            # For text messages
            value = str(self.service.body).strip()  # Ensure string and strip whitespace
            logger.debug(f"Text message value: {value}")

            # Get member ID and channel identifier
            current_state = self.service.user.state.state or {}
            member_id = current_state.get("member_id", "pending")
            channel_id = self.service.user.channel_identifier

            # Log input processing with member and channel context
            audit.log_flow_event(
                "bot_service",
                "input_processing",
                None,
                {
                    "input": value,
                    "type": self.service.message_type,
                    "member_id": member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id
                    }
                },
                "success"
            )

            return value

        except Exception as e:
            logger.error(f"Error extracting input value: {str(e)}")
            # Get member ID and channel identifier
            current_state = self.service.user.state.state or {}
            member_id = current_state.get("member_id", "pending")
            channel_id = self.service.user.channel_identifier

            # Log error with member and channel context
            audit.log_flow_event(
                "bot_service",
                "input_processing_error",
                None,
                {
                    "error": str(e),
                    "member_id": member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id
                    }
                },
                "failure"
            )
            return ""

    def is_greeting(self, text: str) -> bool:
        """Check if message is a greeting"""
        return text.lower() in self.GREETING_KEYWORDS

    def handle_invalid_input(self, flow_step_id: str = None) -> Message:
        """Handle invalid input with appropriate error message"""
        # Get member ID and channel identifier
        current_state = self.service.user.state.state or {}
        member_id = current_state.get("member_id", "pending")
        channel_id = self.service.user.channel_identifier

        # Log error with channel context
        audit.log_flow_event(
            "bot_service",
            "invalid_input",
            flow_step_id,
            {
                "member_id": member_id,
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                }
            },
            "failure"
        )

        # Create error message with proper recipient info
        if flow_step_id == "amount":
            return Message(
                recipient=MessageRecipient(
                    member_id=member_id,
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=TextContent(
                    body="Invalid amount format. Examples:\n"
                    "100     (USD)\n"
                    "USD 100\n"
                    "ZWG 100\n"
                    "XAU 1\n\n"
                    "Please ensure you enter a valid number with an optional currency code."
                )
            )

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body="Invalid input. Please try again with a valid option."
            )
        )
