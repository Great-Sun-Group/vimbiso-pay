"""Handle input component

This component handles Credex handle input with proper validation.
"""

from typing import Any

from core.utils.error_types import ValidationResult

from core.components.base import InputComponent


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

        self.update_state(handle, ValidationResult.success(handle))
        return ValidationResult.success(handle)
