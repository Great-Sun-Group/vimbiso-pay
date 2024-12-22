"""Input handling and validation for WhatsApp messages"""
import logging
from typing import Any, Dict, Union

from core.utils.flow_audit import FlowAuditLogger

from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class InputHandler:
    """Handles message input processing and validation"""

    GREETING_KEYWORDS = {"hi", "hello", "hey", "start"}
    BUTTON_ACTIONS = {"confirm_action"}

    def __init__(self, service: Any):
        self.service = service

    # Map incoming actions to flow types
    ACTION_MAP = {
        "offer_credex": "offer",
        "accept_credex": "accept",
        "decline_credex": "decline",
        "cancel_credex": "cancel"
    }

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

            # Map action to flow type if it exists
            mapped_action = self.ACTION_MAP.get(action, action)
            logger.info(f"Final mapped action: {mapped_action}")
            return mapped_action

        except Exception as e:
            logger.error(f"Error extracting action: {str(e)}")
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

            # Log input processing
            audit.log_flow_event(
                "bot_service",
                "input_processing",
                None,
                {"input": value, "type": self.service.message_type},
                "success"
            )

            return value

        except Exception as e:
            logger.error(f"Error extracting input value: {str(e)}")
            # Log error
            audit.log_flow_event(
                "bot_service",
                "input_processing_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return ""

    def is_greeting(self, text: str) -> bool:
        """Check if message is a greeting"""
        return text.lower() in self.GREETING_KEYWORDS

    def handle_invalid_input(self, flow_step_id: str = None) -> WhatsAppMessage:
        """Handle invalid input with appropriate error message"""
        if flow_step_id == "amount":
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Invalid amount format. Examples:\n"
                "100     (USD)\n"
                "USD 100\n"
                "ZWG 100\n"
                "XAU 1\n\n"
                "Please ensure you enter a valid number with an optional currency code."
            )
        return WhatsAppMessage.create_text(
            self.service.user.mobile_number,
            "Invalid input. Please try again with a valid option."
        )
