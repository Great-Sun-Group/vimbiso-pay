"""Base component interface

This module defines the core Component interface that all components must implement.
Components handle pure UI validation with clear boundaries.
"""

from datetime import datetime
from typing import Any, Dict, Type, Union
from core.utils.error_types import ValidationResult


class Component:
    """Base component interface"""

    def __init__(self, component_type: str):
        """Initialize component with standardized validation tracking"""
        self.type = component_type
        self.value = None
        self.validation_state = {
            "in_progress": False,
            "error": None,
            "attempts": 0,
            "last_attempt": None,
            "operation": None,
            "component": component_type,
            "timestamp": None
        }

    def validate(self, value: Any) -> ValidationResult:
        """Validate component input with standardized tracking

        Args:
            value: Value to validate

        Returns:
            ValidationResult with validation status
        """
        # Track validation attempt with timestamp
        self.validation_state.update({
            "attempts": self.validation_state["attempts"] + 1,
            "last_attempt": value,
            "in_progress": True,
            "operation": "validate",
            "timestamp": datetime.utcnow().isoformat()
        })

        try:
            # Subclasses implement specific validation
            result = self._validate(value)

            # Update state based on result with validation tracking
            if result.valid:
                self.update_state(result.value, result)
            else:
                self.validation_state.update({
                    "in_progress": False,
                    "error": {
                        "message": result.error.get("message"),
                        "field": result.error.get("field"),
                        "details": result.error.get("details", {}),
                        "validation": {
                            "attempts": self.validation_state["attempts"],
                            "last_attempt": value,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                })

            return result

        except Exception as e:
            # Handle unexpected errors with validation tracking
            error = {
                "message": "Validation failed",
                "field": "value",
                "details": {
                    "error": str(e),
                    "validation": {
                        "attempts": self.validation_state["attempts"],
                        "last_attempt": value,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
            self.validation_state.update({
                "in_progress": False,
                "error": error,
                "operation": "validate_error"
            })
            return ValidationResult.failure(
                message=error["message"],
                field=error["field"],
                details=error["details"]
            )

    def _validate(self, value: Any) -> ValidationResult:
        """Component-specific validation logic

        Args:
            value: Value to validate

        Returns:
            ValidationResult with validation status
        """
        raise NotImplementedError

    def get_ui_state(self) -> Dict:
        """Get current UI state with validation tracking

        Returns:
            Dict with component state
        """
        return {
            "type": self.type,
            "value": self.value,
            "validation": self.validation_state
        }

    def update_state(self, value: Any, validation_result: ValidationResult) -> None:
        """Update component state with standardized validation tracking

        Args:
            value: New value
            validation_result: Validation result
        """
        self.value = value
        self.validation_state.update({
            "in_progress": False,
            "error": None,
            "attempts": self.validation_state["attempts"],
            "last_attempt": self.validation_state["last_attempt"],
            "operation": "update",
            "timestamp": datetime.utcnow().isoformat(),
            "validation": {
                "valid": True,
                "value": str(value),
                "attempts": self.validation_state["attempts"],
                "timestamp": datetime.utcnow().isoformat()
            }
        })


class InputComponent(Component):
    """Base class for input components with validation tracking"""

    def __init__(self, component_type: str):
        super().__init__(component_type)

    def _validate_type(self, value: Any, expected_type: Union[Type, tuple], type_name: str) -> ValidationResult:
        """Validate value type with proper error context

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
                details={
                    "expected_type": type_name,
                    "actual_type": str(type(value)),
                    "value": str(value)
                }
            )
        return ValidationResult.success(value)

    def _validate_required(self, value: Any) -> ValidationResult:
        """Validate required value with proper error context

        Args:
            value: Value to validate

        Returns:
            ValidationResult with validation status
        """
        if value is None:
            return ValidationResult.failure(
                message="Value is required",
                field="value",
                details={"error": "missing_required"}
            )

        if isinstance(value, str) and not value.strip():
            return ValidationResult.failure(
                message="Value cannot be empty",
                field="value",
                details={"error": "empty_string"}
            )

        return ValidationResult.success(value)
