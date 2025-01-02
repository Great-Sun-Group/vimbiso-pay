"""Base component interface

This module defines the core Component interface that all components must implement.
Components handle their own validation and data conversion with clear boundaries.
"""

from typing import Any, Dict
from core.utils.exceptions import ComponentException


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

        Raises:
            ComponentException: If conversion fails
        """
        raise NotImplementedError


class InputComponent(Component):
    """Base class for input components"""

    def __init__(self, component_type: str):
        super().__init__(component_type)

    def _validate_type(self, value: Any, expected_type: type, type_name: str) -> None:
        """Validate value type

        Args:
            value: Value to validate
            expected_type: Expected Python type
            type_name: Human readable type name

        Raises:
            ComponentException: If type is invalid
        """
        if not isinstance(value, expected_type):
            raise ComponentException(
                message=f"Value must be {type_name}",
                component=self.type,
                field="value",
                value=str(value)
            )
