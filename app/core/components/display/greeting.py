"""Greeting component for sending culturally-aware greetings

This component handles sending greetings as a separate step in flows.
"""

from typing import Any, Dict

from core.messaging.formatters.greetings import get_random_greeting
from core.utils.error_types import ValidationResult

from core.components.base import Component


class Greeting(Component):
    """Component for sending culturally-aware greetings"""

    def __init__(self):
        super().__init__("greeting")

    def _validate(self, value: Any) -> ValidationResult:
        """Generate greeting - base Component handles validation tracking"""
        # Get greeting text
        greeting = get_random_greeting()

        # Return success with value only - base Component handles validation state
        return ValidationResult.success({
            "greeting": greeting,
            "type": "greeting"  # Include type for flow routing
        })

    def to_message_content(self, value: Dict) -> str:
        """Convert validated value to message content"""
        return value["greeting"]
