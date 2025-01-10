"""Welcome component for registration flow

This component handles the registration welcome screen with proper validation.
"""

from typing import Any

from core.messaging.utils import get_recipient
from core.error.types import ValidationResult

from ..base import DisplayComponent


class Welcome(DisplayComponent):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("welcome")

    def validate_display(self, value: Any) -> ValidationResult:
        """Display welcome message with greeting"""
        try:
            # Send welcome message with button
            from core.messaging.messages import REGISTER
            from core.messaging.types import ButtonContent, Button

            recipient = get_recipient(self.state_manager)
            content = ButtonContent(
                body=REGISTER,
                buttons=[Button(id="become_member", title="Become a Member")]
            )
            # Set awaiting_input before sending message
            self.set_awaiting_input(True)

            send_result = self.state_manager.messaging.send_buttons(
                recipient=recipient,
                content=content
            )

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
