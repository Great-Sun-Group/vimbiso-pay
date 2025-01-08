"""Base confirmation component

This module provides a base component for handling confirmations.
Specific confirmation components extend this with their own context and messaging.
"""

from typing import Any

from core.utils.error_types import ValidationResult
from ..base import Component


class ConfirmBase(Component):
    """Base class for confirmation components"""

    def __init__(self, component_type: str):
        super().__init__(component_type)

    def validate(self, value: Any) -> ValidationResult:
        """Validate confirmation format

        Converts string inputs to boolean and validates type.
        Subclasses handle specific confirmation logic.
        """
        # Handle string inputs
        if isinstance(value, str):
            value = value.lower()
            if value in ("yes", "true", "1"):
                value = True
            elif value in ("no", "false", "0"):
                value = False
            else:
                return ValidationResult.failure(
                    message="Please respond with yes or no",
                    field="confirmation"
                )

        # Validate type
        if not isinstance(value, bool):
            return ValidationResult.failure(
                message="Value must be boolean",
                field="value",
                details={
                    "expected_type": "boolean",
                    "actual_type": str(type(value)),
                    "value": str(value)
                }
            )

        # Let subclass handle specific confirmation
        if not value:
            return ValidationResult.failure(
                message=self.get_rejection_message(),
                field="confirmation"
            )

        return self.handle_confirmation(value)

    def handle_confirmation(self, value: bool) -> ValidationResult:
        """Handle specific confirmation logic

        Args:
            value: Validated boolean value

        Returns:
            ValidationResult with confirmation status
        """
        raise NotImplementedError

    def get_rejection_message(self) -> str:
        """Get message for when confirmation is rejected

        Returns:
            Rejection message
        """
        raise NotImplementedError
