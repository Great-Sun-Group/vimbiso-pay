"""Welcome component for registration flow

This component handles the registration welcome screen with proper validation.
"""

from typing import Any

from core.error.types import ValidationResult
from core.messaging.utils import get_recipient
from core.messaging.types import (
    Button,
    InteractiveContent,
    InteractiveType,
    Message,
    MessageType,
)

from ..base import DisplayComponent


class Welcome(DisplayComponent):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("welcome")

    def validate_display(self, value: Any) -> ValidationResult:
        """Display welcome message with greeting or handle button response"""
        try:
            # Get component data
            component_data = self.state_manager.get_state_value("component_data", {})
            message = component_data.get("data", {}).get("message", {})

            # Handle button response
            if message.get("type") == MessageType.INTERACTIVE.value:
                button = message.get("button", {})
                if button.get("id") == "become_member":
                    # Release flow to move to next component
                    self.set_awaiting_input(False)
                    return ValidationResult.success()
                return ValidationResult.failure(
                    message="Invalid button selection",
                    field="button",
                    details={"error": "invalid_selection"}
                )

            # Send welcome message with button
            from core.messaging.messages import REGISTER

            recipient = get_recipient(self.state_manager)
            content = InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=REGISTER,
                buttons=[Button(id="become_member", title="Become a Member")]
            )
            # Set awaiting_input before sending message
            self.set_awaiting_input(True)

            message = Message(recipient=recipient, content=content)
            send_result = self.state_manager.messaging.send_message(message)

            if send_result:
                return ValidationResult.success()

            # Message wasn't sent successfully - track error in state
            return ValidationResult.failure(
                message="Failed to send welcome message",
                field="messaging",
                details={"error": "send_failed"}
            )

        except Exception as e:
            return ValidationResult.failure(
                message=str(e),
                field="welcome",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )
