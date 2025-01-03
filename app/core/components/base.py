"""Base component interface

This module defines the core Component interface that all components must implement.
Components handle pure UI validation with clear boundaries.
"""

from typing import Any, Dict, Type, Union
from core.utils.error_types import ValidationResult


class Component:
    """Base component interface"""

    def __init__(self, component_type: str):
        self.type = component_type
        self.value = None
        self.validation_state = {
            "in_progress": False,
            "error": None
        }

    def validate(self, value: Any) -> ValidationResult:
        """Validate component input

        Args:
            value: Value to validate

        Returns:
            ValidationResult with validation status
        """
        raise NotImplementedError

    def get_ui_state(self) -> Dict:
        """Get current UI state

        Returns:
            Dict with component state
        """
        return {
            "type": self.type,
            "value": self.value,
            "validation": self.validation_state
        }

    def update_state(self, value: Any, validation_result: ValidationResult) -> None:
        """Update component state

        Args:
            value: New value
            validation_result: Validation result
        """
        self.value = value
        self.validation_state = {
            "in_progress": False,
            "error": validation_result.error
        }


class InputComponent(Component):
    """Base class for input components"""

    def __init__(self, component_type: str):
        super().__init__(component_type)

    def _validate_type(self, value: Any, expected_type: Union[Type, tuple], type_name: str) -> ValidationResult:
        """Validate value type

        Args:
            value: Value to validate
            expected_type: Expected Python type or tuple of types
            type_name: Human readable type name

        Returns:
            ValidationResult with validation status
        """
        if not isinstance(value, expected_type):
            return ValidationResult.failure(
                message=f"Value must be {type_name}",
                field="value",
                details={"actual_type": str(type(value))}
            )
        return ValidationResult.success(value)
