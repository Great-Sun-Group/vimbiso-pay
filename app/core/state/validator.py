"""State validation

This module provides validation for:
- Protected core state
- Current flow/component state
- Validation tracking
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ValidationResult:
    """Result of state validation"""
    is_valid: bool
    error_message: Optional[str] = None


class StateValidator:
    """Validates state structure with clear boundaries"""

    # Protected state fields that can't be modified externally
    PROTECTED_FIELDS = {
        "channel",    # Channel info
        "dashboard",  # Dashboard state
        "action",   # Action state
        "auth"      # Auth state
    }

    # Current state validation rules
    CURRENT_RULES = {
        # Required fields
        "required_fields": {
            "path": str,      # Flow path
            "component": str,  # Component name
            "data": dict     # Component data
        },

        # Optional fields with types
        "optional_fields": {
            "component_result": (type(None), str),
            "awaiting_input": bool
        }
    }

    # Validation tracking rules
    VALIDATION_RULES = {
        "attempts": dict,    # Attempts per operation
        "history": list     # Validation history
    }

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete state structure"""
        # Validate state is dictionary
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate protected state
        for field in cls.PROTECTED_FIELDS:
            if field in state and not isinstance(state[field], dict):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field} must be a dictionary"
                )

        # Validate channel structure if present
        channel = state.get("channel")
        if channel:
            if "type" not in channel or "identifier" not in channel:
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel missing required fields"
                )

        # Validate current state if present
        current = state.get("current")
        if current is not None:
            if not isinstance(current, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Current state must be a dictionary"
                )

            # Validate required fields
            for field, field_type in cls.CURRENT_RULES["required_fields"].items():
                if field not in current:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Missing required field: {field}"
                    )
                if not isinstance(current[field], field_type):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Invalid type for {field}"
                    )

            # Validate optional fields
            for field, field_type in cls.CURRENT_RULES["optional_fields"].items():
                if field in current:
                    if isinstance(field_type, tuple):
                        if not any(isinstance(current[field], t) for t in field_type):
                            return ValidationResult(
                                is_valid=False,
                                error_message=f"Invalid type for {field}"
                            )
                    elif not isinstance(current[field], field_type):
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Invalid type for {field}"
                        )

        # Validate validation tracking if present
        validation = state.get("validation")
        if validation is not None:
            if not isinstance(validation, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Validation must be a dictionary"
                )

            for field, field_type in cls.VALIDATION_RULES.items():
                if field not in validation:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Missing validation field: {field}"
                    )
                if not isinstance(validation[field], field_type):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Invalid type for validation {field}"
                    )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_protected_update(cls, current: Dict[str, Any], updates: Dict[str, Any]) -> ValidationResult:
        """Validate protected field updates"""
        for field in cls.PROTECTED_FIELDS:
            if (
                field in updates and
                field in current and
                updates[field] != current[field]
            ):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Cannot modify protected field: {field}"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_current_state(cls, current: Dict[str, Any]) -> ValidationResult:
        """Validate current state structure"""
        if not isinstance(current, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Current state must be a dictionary"
            )

        # Validate required fields
        for field, field_type in cls.CURRENT_RULES["required_fields"].items():
            if field not in current:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required field: {field}"
                )
            if not isinstance(current[field], field_type):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid type for {field}"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def prepare_state_update(cls, state_manager: Any, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and validate state updates

        Args:
            state_manager: StateManager instance
            updates: State updates to apply

        Returns:
            Validated and prepared state updates

        Raises:
            ComponentException: If updates are invalid
        """
        from core.error.exceptions import ComponentException

        # Validate protected fields
        result = cls.validate_protected_update(state_manager._state, updates)
        if not result.is_valid:
            raise ComponentException(
                message=result.error_message,
                component="state_validator",
                field="protected_fields"
            )

        # Validate current state if present
        if "current" in updates:
            result = cls.validate_current_state(updates["current"])
            if not result.is_valid:
                raise ComponentException(
                    message=result.error_message,
                    component="state_validator",
                    field="current_state"
                )

        # Validate complete state structure
        result = cls.validate_state(updates)
        if not result.is_valid:
            raise ComponentException(
                message=result.error_message,
                component="state_validator",
                field="state_structure"
            )

        return updates


# For backward compatibility
prepare_state_update = StateValidator.prepare_state_update
