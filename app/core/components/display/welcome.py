"""Welcome component for registration flow

This component handles the registration welcome screen.
"""

from typing import Any

from core.error.types import ValidationResult
from core.messaging.types import (Button, InteractiveContent, InteractiveType,
                                  Message, MessageType)
from ..base import DisplayComponent


# Registration template
REGISTER = """Welcome to VimbisoPay 💰

We're your portal 🚪to the credex ecosystem 🌱

Become a member 🌐 and open a free account 💳 to get started 📈"""


class Welcome(DisplayComponent):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("welcome")

    def validate_display(self, value: Any) -> ValidationResult:
        """Display welcome message with greeting or handle button response"""
        try:
            # Handle button response if awaiting input
            if self.state_manager.is_awaiting_input():
                incoming_message = self.state_manager.get_incoming_message()
                if not incoming_message:
                    return ValidationResult.failure(
                        message="No incoming message found",
                        field="message",
                        details={"error": "missing_message"}
                    )

                if incoming_message.get("type") == MessageType.INTERACTIVE.value:
                    text = incoming_message.get("text", {})
                    if text.get("interactive_type") == InteractiveType.BUTTON.value:
                        button = text.get("button", {})
                        if button.get("id") == "become_member":
                            # Release flow to move to next component
                            self.set_awaiting_input(False)
                            return ValidationResult.success()
                    return ValidationResult.failure(
                        message="Invalid button selection",
                        field="button",
                        details={"error": "invalid_selection"}
                    )
                return ValidationResult.failure(
                    message="Invalid message type",
                    field="type",
                    details={"error": "not_interactive"}
                )

            # Send welcome message with button
            content = InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=REGISTER,
                buttons=[Button(id="become_member", title="Become a Member")]
            )
            # Set awaiting_input before sending message
            self.set_awaiting_input(True)

            message = Message(content=content)
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
