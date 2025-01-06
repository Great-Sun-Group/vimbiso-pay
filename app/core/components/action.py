"""Action components with pure UI validation

This module implements action-specific components with pure UI validation.
Business validation happens in services.
"""
from typing import Any, Dict, List

from core.utils.error_types import ValidationResult
from .base import InputComponent


class SelectInput(InputComponent):
    """Selection input with pure UI validation"""

    def __init__(self, items: List[Dict[str, Any]]):
        super().__init__("select_input")
        self.items = items

    def validate(self, value: Any) -> ValidationResult:
        """Validate selection value with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate required
        required_result = self._validate_required(value)
        if not required_result.valid:
            return required_result

        # Convert to int and validate range
        try:
            index = int(value)
            if not (1 <= index <= len(self.items)):
                return ValidationResult.failure(
                    message=f"Selection must be between 1 and {len(self.items)}",
                    field="selection",
                    details={
                        "min": 1,
                        "max": len(self.items),
                        "received": index
                    }
                )
        except ValueError:
            return ValidationResult.failure(
                message="Selection must be a number",
                field="selection",
                details={
                    "expected_type": "number",
                    "received": value
                }
            )

        return ValidationResult.success(value)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        index = int(value) - 1  # Convert to 0-based index
        selected_item = self.items[index]
        return {
            "credex_id": selected_item.get("credexID"),
            "amount": selected_item.get("formattedInitialAmount"),
            "counterparty": selected_item.get("counterpartyAccountName")
        }


class ActionConfirmInput(InputComponent):
    """Action confirmation input with pure UI validation"""

    def __init__(self, action: str, credex_id: str):
        super().__init__("action_confirm_input")
        self.action = action
        self.credex_id = credex_id

    def validate(self, value: Any) -> ValidationResult:
        """Validate confirmation value with proper tracking"""
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
                    field="confirmation",
                    details={
                        "valid_values": ["yes", "no", "true", "false", "1", "0"],
                        "received": value
                    }
                )

        # Validate type
        type_result = self._validate_type(value, bool, "boolean")
        if not type_result.valid:
            return type_result

        return ValidationResult.success(value)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        if isinstance(value, str):
            value = value.lower() in ("yes", "true", "1")

        return {
            "confirmed": value,
            "action": self.action,
            "credex_id": self.credex_id
        }
