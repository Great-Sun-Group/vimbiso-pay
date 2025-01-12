"""Handle input component

This component handles Credex handle input with proper validation.
"""

from typing import Any

from core.error.types import ValidationResult
from ..base import InputComponent


# Handle prompt template
HANDLE_PROMPT = "Enter account 💳 handle:"


class HandleInput(InputComponent):
    """Handle input with pure UI validation"""

    def __init__(self):
        super().__init__("handle_input")

    def validate(self, value: Any) -> ValidationResult:
        """Validate handle format only

        Only checks basic format requirements:
        - Must be string
        - Must not be empty
        - Must be <= 30 chars

        Business validation (availability etc) happens in service layer
        """
        # If no value provided, we're being activated - await input
        if value is None:
            self.set_awaiting_input(True)
            return ValidationResult.success(None)

        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate basic format
        handle = value.strip()
        if not handle:
            return ValidationResult.failure(
                message="Handle required",
                field="handle"
            )

        if len(handle) > 30:
            return ValidationResult.failure(
                message="Handle too long (max 30 chars)",
                field="handle"
            )

        # Update state and release our hold on the flow
        self.update_state(handle, ValidationResult.success(handle))
        self.set_awaiting_input(False)  # Release our own hold
        return ValidationResult.success(handle)
