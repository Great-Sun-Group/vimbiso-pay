"""Core input components

This module implements pure UI input components with format validation.
Each component handles a specific input type with clear boundaries.
Business logic validation happens in services.
"""

from typing import Any, List
from .base import InputComponent
from core.utils.error_types import ValidationResult


class ButtonInput(InputComponent):
    """Button input with pure UI validation"""

    def __init__(self):
        super().__init__("button_input")

    def validate(self, value: Any) -> ValidationResult:
        """Validate button input format"""
        try:
            # Extract button ID from interactive message
            if isinstance(value, dict):
                interactive = value.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    button_id = interactive.get("button_reply", {}).get("id")
                    if not button_id:
                        return ValidationResult.failure(
                            message="Missing button ID",
                            field="button"
                        )
                    self.update_state(button_id, ValidationResult.success(button_id))
                    return ValidationResult.success(button_id)
                return ValidationResult.failure(
                    message="Invalid button type",
                    field="button"
                )

            # Handle direct button ID string
            type_result = self._validate_type(value, str, "text")
            if not type_result.valid:
                return type_result

            button_id = value.strip()
            if not button_id:
                return ValidationResult.failure(
                    message="Empty button ID",
                    field="button"
                )

            self.update_state(button_id, ValidationResult.success(button_id))
            return ValidationResult.success(button_id)

        except Exception:
            return ValidationResult.failure(
                message="Invalid button input",
                field="button"
            )


class AmountInput(InputComponent):
    """Amount input with pure UI validation"""

    def __init__(self):
        super().__init__("amount_input")

    def validate(self, value: Any) -> ValidationResult:
        """Validate amount format only

        Only checks basic format requirements:
        - Must be numeric
        - Must be positive
        - Must parse as float

        Business validation (limits etc) happens in service layer
        """
        try:
            # Validate type
            type_result = self._validate_type(value, (int, float, str), "numeric")
            if not type_result.valid:
                return type_result

            # Convert to float
            amount = float(value) if isinstance(value, str) else value

            # Basic format validation
            if amount <= 0:
                return ValidationResult.failure(
                    message="Amount must be positive",
                    field="amount"
                )

            self.update_state(str(amount), ValidationResult.success(amount))
            return ValidationResult.success(amount)

        except ValueError:
            return ValidationResult.failure(
                message="Invalid amount format",
                field="amount"
            )


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


class SelectInput(InputComponent):
    """Selection input with pure UI validation"""

    def __init__(self, options: List[str]):
        super().__init__("select_input")
        self.options = options

    def validate(self, value: Any) -> ValidationResult:
        """Validate selection format only

        Only checks that selection is in allowed options.
        Business validation happens in service layer.
        """
        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate selection exists
        if value not in self.options:
            return ValidationResult.failure(
                message="Invalid selection",
                field="selection",
                details={"valid_options": self.options}
            )

        self.update_state(value, ValidationResult.success(value))
        return ValidationResult.success(value)


class ConfirmInput(InputComponent):
    """Confirmation input with pure UI validation"""

    def __init__(self):
        super().__init__("confirm_input")

    def validate(self, value: Any) -> ValidationResult:
        """Validate confirmation format only

        Converts string inputs to boolean and validates type.
        Business validation happens in service layer.
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
        type_result = self._validate_type(value, bool, "boolean")
        if not type_result.valid:
            return type_result

        self.update_state(value, ValidationResult.success(value))
        return ValidationResult.success(value)
