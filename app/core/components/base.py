"""Base component interfaces

This module defines the core Component interfaces that all components extend.
Each interface handles a specific type of component with clear validation patterns.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Type, Union

from core.utils.error_types import ValidationResult
from core.utils.exceptions import ComponentException


class Component:
    """Base component interface"""

    def __init__(self, component_type: str):
        """Initialize component with standardized validation tracking"""
        self.type = component_type
        self.value = None
        self.state_manager = None
        self.validation_state = {
            "in_progress": False,
            "error": None,
            "attempts": 0,
            "last_attempt": None,
            "operation": None,
            "component": component_type,
            "timestamp": None
        }

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing state data

        Args:
            state_manager: State manager instance

        Raises:
            ComponentException: If state manager is not properly initialized
        """
        if not state_manager:
            raise ComponentException(
                message="State manager is required",
                component=self.type,
                field="state_manager",
                value="None"
            )

        if not hasattr(state_manager, 'messaging') or state_manager.messaging is None:
            raise ComponentException(
                message="State manager messaging service not initialized",
                component=self.type,
                field="state_manager.messaging",
                value=str(state_manager)
            )

        self.state_manager = state_manager

    def validate(self, value: Any) -> ValidationResult:
        """Validate component input with standardized tracking

        Args:
            value: Value to validate

        Returns:
            ValidationResult with validation status
        """
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": self.type}
            )

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
                error_details = {}
                if result.error:
                    error_details = {
                        "message": result.error.get("message"),
                        "field": result.error.get("field"),
                        "details": result.error.get("details", {})
                    }

                self.validation_state.update({
                    "in_progress": False,
                    "error": {
                        **error_details,
                        "validation": {
                            "attempts": self.validation_state["attempts"],
                            "last_attempt": value,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    } if error_details else None
                })

            return result

        except Exception as e:
            # Update validation state with error details
            validation_state = {
                "in_progress": False,
                "error": str(e),
                "operation": "validate_error",
                "attempts": self.validation_state["attempts"],
                "last_attempt": value,
                "timestamp": datetime.utcnow().isoformat(),
                "component": self.type
            }
            self.validation_state.update(validation_state)

            # Raise ComponentException with complete validation context
            raise ComponentException(
                message=str(e),
                component=self.type,
                field="value",
                value=str(value),
                validation=validation_state
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

    def to_message_content(self, value: Dict) -> str:
        """Convert component result to message content

        Args:
            value: Component result value

        Returns:
            str: Formatted message content

        Raises:
            NotImplementedError: If component doesn't implement conversion
        """
        raise NotImplementedError

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


class DisplayComponent(Component):
    """Base class for display components"""

    def __init__(self, component_type: str):
        super().__init__(component_type)

    def _validate(self, value: Any) -> ValidationResult:
        """Validate display data with proper tracking"""
        logger = logging.getLogger(__name__)
        try:
            # Log validation attempt
            logger.info(f"Validating display component {self.type} with value: {value}")

            # Subclasses implement specific validation
            result = self.validate_display(value)

            # Log validation result
            logger.info(f"Display validation result: {result}")
            return result

        except Exception as e:
            logger.error(f"Display validation error in {self.type}: {str(e)}")
            raise

    def validate_display(self, value: Any) -> ValidationResult:
        """Component-specific display validation logic"""
        raise NotImplementedError


class InputComponent(Component):
    """Base class for input components"""

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


class ApiComponent(Component):
    """Base class for API components"""

    def __init__(self, component_type: str):
        super().__init__(component_type)

    def _validate(self, value: Any) -> ValidationResult:
        """Validate API call with proper tracking"""
        logger = logging.getLogger(__name__)
        try:
            # Log validation attempt
            logger.info(f"Validating API component {self.type} with value: {value}")

            # Subclasses implement specific validation
            result = self.validate_api_call(value)

            # Log validation result
            logger.info(f"API validation result: {result}")
            return result

        except Exception as e:
            logger.error(f"API validation error in {self.type}: {str(e)}")
            raise

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Component-specific API validation logic"""
        raise NotImplementedError
