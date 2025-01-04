"""Greeting component for sending culturally-aware greetings

This component handles sending greetings as a separate step in flows.
"""

from typing import Any, Dict

from core.messaging.greetings import get_random_greeting
from core.utils.error_types import ValidationResult

from .base import Component


class GreetingComponent(Component):
    """Component for sending culturally-aware greetings"""

    def __init__(self):
        super().__init__("greeting")

    def _validate(self, value: Any) -> ValidationResult:
        """No validation needed for greeting - always valid"""
        return ValidationResult.success({
            "greeting": get_random_greeting()
        })

    def to_message_content(self, value: Dict) -> str:
        """Convert validated value to message content"""
        return value["greeting"]
