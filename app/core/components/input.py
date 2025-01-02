"""Core input components

This module implements the core input components with specific validation and conversion logic.
Each component handles a specific input type with clear boundaries.
"""

from typing import Any, Dict

from core.utils.exceptions import ValidationException
from .base import InputComponent


class AmountInput(InputComponent):
    """Amount input with validation"""

    def __init__(self):
        super().__init__("amount_input")

    def validate(self, value: Any) -> Dict:
        """Validate amount value"""
        try:
            # Validate type
            self._validate_type(value, (int, float, str), "numeric")

            # Convert to float
            amount = float(value) if isinstance(value, str) else value

            # Validate value
            if amount <= 0:
                raise ValidationException(
                    message="Amount must be positive",
                    component=self.type,
                    field="amount",
                    value=str(value)
                )

            return {"valid": True}

        except ValueError:
            raise ValidationException(
                message="Invalid amount format",
                component=self.type,
                field="amount",
                value=str(value)
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified amount"""
        return {
            "amount": float(value)
        }


class HandleInput(InputComponent):
    """Handle input with validation"""

    def __init__(self):
        super().__init__("handle_input")

    def validate(self, value: Any) -> Dict:
        """Validate handle value"""
        # Validate type
        self._validate_type(value, str, "text")

        # Validate content
        handle = value.strip()
        if not handle:
            raise ValidationException(
                message="Handle required",
                component=self.type,
                field="handle",
                value=str(value)
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified handle"""
        return {
            "handle": value.strip()
        }


class SelectInput(InputComponent):
    """Selection input with validation"""

    def __init__(self, options: list):
        super().__init__("select_input")
        self.options = options

    def validate(self, value: Any) -> Dict:
        """Validate selection value"""
        # Validate type
        self._validate_type(value, str, "text")

        # Validate selection
        if value not in self.options:
            raise ValidationException(
                message="Invalid selection",
                component=self.type,
                field="selection",
                value=str(value)
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified selection"""
        return {
            "selected_id": value
        }


class ConfirmInput(InputComponent):
    """Confirmation input with validation"""

    def __init__(self):
        super().__init__("confirm_input")

    def validate(self, value: Any) -> Dict:
        """Validate confirmation value"""
        # Handle string inputs
        if isinstance(value, str):
            value = value.lower()
            if value in ("yes", "true", "1"):
                value = True
            elif value in ("no", "false", "0"):
                value = False
            else:
                raise ValidationException(
                    message="Invalid confirmation value",
                    component=self.type,
                    field="confirmation",
                    value=str(value)
                )

        # Validate type
        self._validate_type(value, bool, "boolean")

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation"""
        if isinstance(value, str):
            value = value.lower() in ("yes", "true", "1")

        return {
            "confirmed": value
        }
