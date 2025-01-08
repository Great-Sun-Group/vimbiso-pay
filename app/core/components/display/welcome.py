"""Welcome component for registration flow

This component handles the registration welcome screen with proper validation.
"""

from typing import Any

from core.messaging.formatters.formatters import RegistrationFormatters
from core.utils.error_types import ValidationResult

from ..base import DisplayComponent


class Welcome(DisplayComponent):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("welcome")

    def validate_display(self, value: Any) -> ValidationResult:
        """Simple validation for welcome step"""
        return ValidationResult.success({})

    def to_message_content(self, value: Any) -> str:
        """Convert to message content using RegistrationFormatters"""
        return RegistrationFormatters.format_welcome()
