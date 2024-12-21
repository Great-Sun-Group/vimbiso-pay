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

    def get_action(self) -> str:
        """Extract action from message"""
        # Handle interactive messages
        if self.service.message_type == "interactive":
            interactive = self.service.message.get("interactive", {})
            if interactive.get("type") == "list_reply":
                return interactive.get("list_reply", {}).get("id", "").lower()
            elif interactive.get("type") == "button_reply":
                return interactive.get("button_reply", {}).get("id", "").lower()

        # For text messages
        return self.service.body.strip().lower()

    def extract_input_value(self) -> Union[str, Dict]:
        """Extract input value based on message type"""
        if self.service.message_type == "interactive":
            interactive = self.service.message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                return interactive.get("button_reply", {})
            elif interactive.get("type") == "list_reply":
                return interactive.get("list_reply", {})

        return self.service.body

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
