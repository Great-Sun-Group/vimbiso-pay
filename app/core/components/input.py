"""Core input components

This module implements the core input components with specific validation and conversion logic.
Each component handles a specific input type with clear boundaries.
"""

from typing import Any, Dict
from .base import InputComponent


class ButtonInput(InputComponent):
    """Button input with validation"""

    def __init__(self):
        super().__init__("button_input")

    def validate(self, value: Any) -> Dict:
        """Validate button input"""
        try:
            # Extract button ID from interactive message
            if isinstance(value, dict):
                interactive = value.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    button_id = interactive.get("button_reply", {}).get("id")
                    if not button_id:
                        return self._handle_validation_error(
                            value=str(value),
                            message="Missing button ID",
                            field="button"
                        )
                    return {"valid": True}
                return self._handle_validation_error(
                    value=str(value),
                    message="Invalid button type",
                    field="button"
                )

            # Handle direct button ID string
            type_validation = self._validate_type(value, str, "text")
            if "error" in type_validation:
                return type_validation

            button_id = value.strip()
            if not button_id:
                return self._handle_validation_error(
                    value=str(value),
                    message="Empty button ID",
                    field="button"
                )

            return {"valid": True}

        except Exception:
            return self._handle_validation_error(
                value=str(value),
                message="Invalid button input",
                field="button"
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified button data"""
        if isinstance(value, dict):
            return {
                "button_id": value.get("interactive", {}).get("button_reply", {}).get("id")
            }
        return {
            "button_id": value.strip()
        }


class AmountInput(InputComponent):
    """Amount input with validation"""

    def __init__(self):
        super().__init__("amount_input")

    def validate(self, value: Any) -> Dict:
        """Validate amount value"""
        try:
            # Validate type
            type_validation = self._validate_type(value, (int, float, str), "numeric")
            if "error" in type_validation:
                return type_validation

            # Convert to float
            amount = float(value) if isinstance(value, str) else value

            # Validate value
            if amount <= 0:
                return self._handle_validation_error(
                    value=str(value),
                    message="Amount must be positive",
                    field="amount"
                )

            return {"valid": True}

        except ValueError:
            return self._handle_validation_error(
                value=str(value),
                message="Invalid amount format",
                field="amount"
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
        type_validation = self._validate_type(value, str, "text")
        if "error" in type_validation:
            return type_validation

        # Validate content
        handle = value.strip()
        if not handle:
            return self._handle_validation_error(
                value=str(value),
                message="Handle required",
                field="handle"
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
        type_validation = self._validate_type(value, str, "text")
        if "error" in type_validation:
            return type_validation

        # Validate selection
        if value not in self.options:
            return self._handle_validation_error(
                value=str(value),
                message="Invalid selection",
                field="selection"
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
                return self._handle_validation_error(
                    value=str(value),
                    message="Invalid confirmation value",
                    field="confirmation"
                )

        # Validate type
        type_validation = self._validate_type(value, bool, "boolean")
        if "error" in type_validation:
            return type_validation

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation"""
        if isinstance(value, str):
            value = value.lower() in ("yes", "true", "1")

        return {
            "confirmed": value
        }
