"""Amount input component

This component handles amount input with proper validation.
"""

from typing import Any, Dict

from core.error.types import ValidationResult

from ..base import InputComponent

# Amount prompt template
AMOUNT_PROMPT = """💸 *What offer amount and denomination?*
✨ Defaults to USD: *9 || 99 || 9999.99 || 0.99*
✨ Denom placement: *99 ZWG || ZWG 99*
✨ Denoms: *CXX || XAU || USD || CAD || ZWG*"""


class AmountInput(InputComponent):
    """Amount input with pure UI validation"""

    def __init__(self):
        super().__init__("amount_input")

    def _validate(self, value: Any) -> ValidationResult:
        """Validate amount format only

        Only checks basic format requirements:
        - Must be numeric
        - Must be positive
        - Must parse as float

        Business validation (limits etc) happens in service layer
        """
        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})
        incoming_message = current_data.get("incoming_message")

        # Initial activation - send prompt
        if not current_data.get("awaiting_input"):
            self.state_manager.messaging.send_text(
                text=AMOUNT_PROMPT
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

        try:
            # Convert to float
            amount = float(text.strip())

            # Basic format validation
            if amount <= 0:
                return ValidationResult.failure(
                    message="Amount must be positive",
                    field="amount",
                    details={"amount": amount}
                )

            # Store validated amount in component_data.data for subsequent components
            self.update_component_data(
                data={"amount": str(amount)},
                awaiting_input=False
            )
            return ValidationResult.success(amount)

        except ValueError:
            return ValidationResult.failure(
                message="Invalid amount format",
                field="amount",
                details={"text": text}
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified amount"""
        return {
            "amount": str(float(value))
        }
