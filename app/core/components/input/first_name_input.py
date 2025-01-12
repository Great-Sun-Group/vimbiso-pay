"""First name input component

This component handles first name input with proper validation.
"""

from typing import Any, Dict

from core.components.base import InputComponent
from core.error.types import ValidationResult


class FirstNameInput(InputComponent):
    """First name input with validation"""

    def __init__(self):
        super().__init__("firstname_input")

    def validate(self, value: Any) -> ValidationResult:
        """Validate first name with proper tracking"""
        # If no value provided, we're being activated - send prompt and await input
        if value is None:
            self.state_manager.messaging.send_text(
                body="Please enter your first name:"
            )
            self.set_awaiting_input(True)
            return ValidationResult.success(None)

        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate required
        required_result = self._validate_required(value)
        if not required_result.valid:
            return required_result

        # Validate length
        firstname = value.strip()
        if len(firstname) < 3 or len(firstname) > 50:
            return ValidationResult.failure(
                message="First name must be between 3 and 50 characters",
                field="firstname",
                details={
                    "min_length": 3,
                    "max_length": 50,
                    "actual_length": len(firstname)
                }
            )

        # Store validated firstname in component_data.data for subsequent components
        self.update_component_data(
            data={"firstname": firstname},
            awaiting_input=False
        )
        return ValidationResult.success(firstname)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified first name"""
        return {
            "firstname": value.strip()
        }
