"""Action components with validation"""
from typing import Any, Dict, List

from .base import InputComponent


class SelectInput(InputComponent):
    """Selection input with validation"""

    def __init__(self, items: List[Dict[str, Any]]):
        super().__init__("select_input")
        self.items = items

    def validate(self, value: Any) -> Dict:
        """Validate selection value"""
        try:
            # Validate type
            type_validation = self._validate_type(value, str, "text")
            if "error" in type_validation:
                return type_validation

            # Convert to int and validate range
            try:
                index = int(value)
                if not (1 <= index <= len(self.items)):
                    return self._handle_validation_error(
                        value=str(value),
                        message=f"Selection must be between 1 and {len(self.items)}",
                        field="selection"
                    )
            except ValueError:
                return self._handle_validation_error(
                    value=str(value),
                    message="Selection must be a number",
                    field="selection"
                )

            return {"valid": True}

        except Exception:
            return self._handle_validation_error(
                value=str(value),
                message="Invalid selection",
                field="selection"
            )

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
    """Action confirmation input with validation"""

    def __init__(self, action: str, credex_id: str):
        super().__init__("action_confirm_input")
        self.action = action
        self.credex_id = credex_id

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
                    message="Please respond with yes or no",
                    field="confirmation"
                )

        # Validate type
        type_validation = self._validate_type(value, bool, "boolean")
        if "error" in type_validation:
            return type_validation

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        if isinstance(value, str):
            value = value.lower() in ("yes", "true", "1")

        return {
            "confirmed": value,
            "action": self.action,
            "credex_id": self.credex_id
        }
