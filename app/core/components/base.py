"""Base component interface

This module defines the core Component interface that all components must implement.
Components handle their own validation and data conversion with clear boundaries.
"""

from typing import Any, Dict, Type, Union
from core.utils.error_handler import ErrorHandler


class Component:
    """Base component interface"""

    def __init__(self, component_type: str):
        self.type = component_type

    def validate(self, value: Any) -> Dict:
        """Validate component input

        Returns:
            On success: {"valid": True}
            On error: {
                "error": {
                    "type": "component",
                    "message": str,
                    "details": {...}
                }
            }
        """
        raise NotImplementedError

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data

        Args:
            value: Validated input value

        Returns:
            Dict with converted data
        """
        raise NotImplementedError


class InputComponent(Component):
    """Base class for input components"""

    def __init__(self, component_type: str):
        super().__init__(component_type)

    def _validate_type(self, value: Any, expected_type: Union[Type, tuple], type_name: str) -> None:
        """Validate value type

        Args:
            value: Value to validate
            expected_type: Expected Python type or tuple of types
            type_name: Human readable type name

        Returns:
            Dict with error if validation fails
        """
        if not isinstance(value, expected_type):
            return ErrorHandler.handle_component_error(
                component=self.type,
                field="value",
                value=str(value),
                message=f"Value must be {type_name}"
            )
        return {"valid": True}

    def _handle_validation_error(self, value: Any, message: str, field: str = "value") -> Dict:
        """Handle component validation error

        Args:
            value: Invalid value
            message: Error message
            field: Field name that failed validation

        Returns:
            Dict with error details
        """
        return ErrorHandler.handle_component_error(
            component=self.type,
            field=field,
            value=str(value),
            message=message
        )
