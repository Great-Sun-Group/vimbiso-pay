"""Last name input component

This component handles last name input with proper validation.
"""

from typing import Any, Dict

from core.error.types import ValidationResult

from core.components.base import InputComponent


class LastNameInput(InputComponent):
    """Last name input with validation"""

    def __init__(self):
        super().__init__("lastname_input")

    def validate(self, value: Any) -> ValidationResult:
        """Validate last name with proper tracking"""
        # If no value provided, we're being activated - await input
        if value is None:
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
        lastname = value.strip()
        if len(lastname) < 3 or len(lastname) > 50:
            return ValidationResult.failure(
                message="Last name must be between 3 and 50 characters",
                field="lastname",
                details={
                    "min_length": 3,
                    "max_length": 50,
                    "actual_length": len(lastname)
                }
            )

        # Get existing data (should have firstname from previous component)
        current_data = self.state_manager.get_state_value("component_data", {}).get("data", {})

        # Add lastname while preserving firstname
        self.update_component_data(
            data={**current_data, "lastname": lastname},
            awaiting_input=False
        )
        return ValidationResult.success(lastname)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified last name"""
        return {
            "lastname": value.strip()
        }
