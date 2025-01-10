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
            # Send welcome message
            from core.messaging.messages import REGISTER
            recipient = get_recipient(self.state_manager)
            send_result = self.state_manager.messaging.send_text(
                recipient=recipient,
                text=REGISTER
            )

            if send_result:
                # Just return success to progress flow
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
