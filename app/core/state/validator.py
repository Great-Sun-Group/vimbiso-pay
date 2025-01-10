"""State validation with clear boundaries

This module provides simple state validation focused on:
- Core state structure
- Flow state validation
- Channel validation
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

    # Core state fields that can't be modified once set
    CORE_FIELDS = {"member_id", "channel", "jwt_token"}

    # Flow validation rules
    FLOW_RULES = {
        # Required fields in flow_data
        "required_fields": {
            "flow_type": str,
            "handler_type": str,
            "step": str,
            "step_index": int,
            "total_steps": int
        },

        # Required fields in active_component
        "component_fields": {
            "type": str,
            "validation": {
                "in_progress": bool,
                "error": (type(None), dict),
                "attempts": int,
                "last_attempt": (type(None), str, int, float, bool, dict, list)
            }
        },

        # Valid handler types
        "handler_types": {"member", "account", "credex"},

        # Flow type validation is now handled by FlowRegistry
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

        # Validate channel exists and structure
        if "channel" not in state:
            return ValidationResult(
                is_valid=False,
                error_message="Missing required field: channel"
            )

        channel = state["channel"]
        if not isinstance(channel, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Channel must be a dictionary"
            )

        if "type" not in channel or "identifier" not in channel:
            return ValidationResult(
                is_valid=False,
                error_message="Channel missing required fields"
            )

        # Validate flow state if present
        if "flow_data" in state and state["flow_data"] is not None:
            flow_data = state["flow_data"]
            if not isinstance(flow_data, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Flow data must be a dictionary"
                )

            # Validate required fields
            for field, field_type in cls.FLOW_RULES["required_fields"].items():
                if field not in flow_data:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Missing required field: {field}"
                    )
                if not isinstance(flow_data[field], field_type):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Invalid type for {field}"
                    )

            # Validate handler type
            if flow_data["handler_type"] not in cls.FLOW_RULES["handler_types"]:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid handler type: {flow_data['handler_type']}"
                )

            # Validate step index
            if not (0 <= flow_data["step_index"] < flow_data["total_steps"]):
                return ValidationResult(
                    is_valid=False,
                    error_message="Invalid step index"
                )

            # Validate component state
            component = flow_data.get("active_component")
            if not component or not isinstance(component, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Invalid component state"
                )

            for field, field_type in cls.FLOW_RULES["component_fields"].items():
                if field not in component:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Missing component field: {field}"
                    )

                if field == "validation":
                    validation = component[field]
                    if not isinstance(validation, dict):
                        return ValidationResult(
                            is_valid=False,
                            error_message="Invalid validation state"
                        )

                    for val_field, val_type in field_type.items():
                        if val_field not in validation:
                            return ValidationResult(
                                is_valid=False,
                                error_message=f"Missing validation field: {val_field}"
                            )
                        if not isinstance(validation[val_field], val_type):
                            if isinstance(val_type, tuple):
                                if not any(isinstance(validation[val_field], t) for t in val_type):
                                    return ValidationResult(
                                        is_valid=False,
                                        error_message=f"Invalid type for {val_field}"
                                    )
                            else:
                                return ValidationResult(
                                    is_valid=False,
                                    error_message=f"Invalid type for {val_field}"
                                )
                else:
                    if not isinstance(component[field], field_type):
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Invalid type for component {field}"
                        )

            # Validate data structure
            if "data" in flow_data and not isinstance(flow_data["data"], dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Flow data must be a dictionary"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_core_fields(cls, current: Dict[str, Any], updates: Dict[str, Any]) -> ValidationResult:
        """Validate core field updates"""
        for field in cls.CORE_FIELDS:
            if (
                field in updates and
                field in current and
                updates[field] != current[field]
            ):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Cannot modify core field: {field}"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_flow_state(cls, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate flow state structure"""
        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Validate required fields
        for field, field_type in cls.FLOW_RULES["required_fields"].items():
            if field not in flow_data:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required field: {field}"
                )
            if not isinstance(flow_data[field], field_type):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid type for {field}"
                )

        # Validate handler type
        if flow_data["handler_type"] not in cls.FLOW_RULES["handler_types"]:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid handler type: {flow_data['handler_type']}"
            )

        # Validate step index
        if not (0 <= flow_data["step_index"] < flow_data["total_steps"]):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid step index"
            )

        return ValidationResult(is_valid=True)
