"""Welcome component for registration flow

This component handles the registration welcome screen.
"""

from typing import Any

from core.error.types import ValidationResult
from core.messaging.types import Button

from ..base import DisplayComponent

# Registration template
REGISTER = """Welcome to VimbisoPay 💰

We're your portal 🚪to the credex ecosystem 🌱

Become a member 🌐 and open a free account 💳 to get started 📈"""


class Welcome(DisplayComponent):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("welcome")

    def validate_display(self, response: Any) -> ValidationResult:
        """Validate become_member button press or send initial welcome message

        Args:
            response: Ignored since headquarters always calls validate(None)
        """
        try:
            # Get current state
            current_data = self.state_manager.get_state_value("component_data", {})
            awaiting = current_data.get("awaiting_input", False)
            incoming_message = current_data.get("incoming_message")

            # If we have an incoming message and we're awaiting input, validate button press
            if incoming_message and awaiting:
                # Validate it's an interactive button message
                if incoming_message.get("type") != "interactive":
                    return ValidationResult.failure(
                        message="Expected interactive message",
                        field="type",
                        details={"message": incoming_message}
                    )

                # Get button info
                text = incoming_message.get("text", {})
                if text.get("interactive_type") != "button":
                    return ValidationResult.failure(
                        message="Expected button response",
                        field="interactive_type",
                        details={"text": text}
                    )

                # Check button ID
                button = text.get("button", {})
                if button.get("id") != "become_member":
                    return ValidationResult.failure(
                        message="Invalid response - please click the Become a Member button",
                        field="button",
                        details={"button": button}
                    )

                # Valid button press - allow flow to progress
                self.set_awaiting_input(False)
                return ValidationResult.success()

            # No incoming message or not awaiting input - send welcome message
            if not awaiting:
                self.state_manager.messaging.send_interactive(
                    body=REGISTER,
                    buttons=[Button(
                        id="become_member",
                        title="Become a Member"
                    )]
                )
                self.set_awaiting_input(True)
            return ValidationResult.success()

        except Exception as e:
            return ValidationResult.failure(
                message=str(e),
                field="welcome",
                details={
                    "component": self.type,
                    "error": str(e),
                    "state": self.state_manager.get_state_value("component_data", {})
                }
            )
