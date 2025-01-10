"""Greeting component for sending culturally-aware greetings

This component handles sending greetings as a separate step in flows.
"""

from typing import Any, Dict

from core.messaging.formatters.greetings import get_random_greeting
from core.messaging.utils import get_recipient
from core.utils.error_types import ValidationResult
from core.error.exceptions import ComponentException

from ..base import DisplayComponent


class Greeting(DisplayComponent):
    """Component for sending culturally-aware greetings"""

    def __init__(self):
        super().__init__("greeting")

    def validate_display(self, value: Any) -> ValidationResult:
        """Generate and send greeting with validation tracking"""
        try:
            # Display Phase - Send greeting
            greeting = get_random_greeting()
            recipient = get_recipient(self.state_manager)
            # Send greeting
            send_result = self.state_manager.messaging.send_text(
                recipient=recipient,
                text=greeting
            )

            if send_result:
                # Just return success to progress flow
                return ValidationResult.success()

            # Message wasn't sent successfully - track error in state
            return ValidationResult.failure(
                message="Failed to send greeting message",
                field="messaging",
                details={
                    "greeting": greeting,
                    "error": "send_failed"
                }
            )
        except ComponentException as e:
            # Pass through ComponentException with proper error context
            if hasattr(e, 'details'):
                raise ComponentException(
                    message=str(e),
                    component=self.type,
                    field=e.details.get("field", "messaging"),
                    value=e.details.get("value", str(greeting))
                )
            # Handle case where details aren't available
            raise ComponentException(
                message=str(e),
                component=self.type,
                field="messaging",
                value=str(greeting)
            )
        except Exception as e:
            # Return validation failure with error context
            return ValidationResult.failure(
                message=str(e),
                field="greeting",
                details={
                    "component": self.type,
                    "error": str(e),
                    "value": str(greeting)
                }
            )

    def to_message_content(self, value: Dict) -> str:
        """Convert validated value to message content"""
        if not value or not isinstance(value, dict):
            return "Processing your request..."
        return value.get("message", "Processing your request...")
