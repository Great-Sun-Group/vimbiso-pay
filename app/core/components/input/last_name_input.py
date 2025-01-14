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

    def _validate(self, value: Any) -> ValidationResult:
        """Validate last name with proper tracking"""
        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})
        incoming_message = current_data.get("incoming_message")

        # Initial activation - send prompt
        if not current_data.get("awaiting_input"):
            self.state_manager.messaging.send_text(
                text="👍🏿 And your last name?"
            )
            self.set_awaiting_input(True)
            return ValidationResult.success(None)

        # Process input
        if not incoming_message:
            return ValidationResult.success(None)

        # Get text from message
        if not isinstance(incoming_message, dict):
            return ValidationResult.failure(
                message="Expected text message",
                field="type",
                details={"message": incoming_message}
            )

        text = incoming_message.get("text", {}).get("body", "")
        if not text:
            return ValidationResult.failure(
                message="No text provided",
                field="text",
                details={"message": incoming_message}
            )

        # Validate length
        lastname = text.strip()
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
        self.update_data({**current_data, "lastname": lastname})

        # Release input wait
        self.set_awaiting_input(False)
        return ValidationResult.success(lastname)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified last name"""
        return {
            "lastname": value.strip()
        }
