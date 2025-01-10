"""Amount input component

This component handles amount input with proper validation.
"""

from typing import Any

from core.error.types import ValidationResult

from ..base import InputComponent


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
        # If no value provided, we're being activated - await input
        if value is None:
            self.set_awaiting_input(True)
            return ValidationResult.success(None)

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

            # Update state and release our hold on the flow
            self.update_state(str(amount), ValidationResult.success(amount))
            self.set_awaiting_input(False)  # Release our own hold
            return ValidationResult.success(amount)

        except ValueError:
            return ValidationResult.failure(
                message="Invalid amount format",
                field="amount"
            )
