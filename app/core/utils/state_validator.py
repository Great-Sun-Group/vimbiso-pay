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

    # Valid flow types and their steps
    FLOW_TYPES = {
        "offer": ["amount", "handle", "confirm"],
        "accept": ["select", "confirm"],
        "decline": ["select", "confirm"],
        "cancel": ["select", "confirm"]
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

            # Validate flow type
            flow_type = flow_data.get("flow_type")
            if not flow_type:
                return ValidationResult(
                    is_valid=False,
                    error_message="Flow type required"
                )

            if flow_type not in cls.FLOW_TYPES:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid flow type: {flow_type}"
                )

            # Validate step
            step = flow_data.get("step")
            if not step:
                return ValidationResult(
                    is_valid=False,
                    error_message="Flow step required"
                )

            if step not in cls.FLOW_TYPES[flow_type]:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid step {step} for flow {flow_type}"
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
    def validate_flow_state(cls, flow_type: str, step: str) -> ValidationResult:
        """Validate flow type and step"""
        if flow_type not in cls.FLOW_TYPES:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid flow type: {flow_type}"
            )

        if step not in cls.FLOW_TYPES[flow_type]:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid step {step} for flow {flow_type}"
            )

        return ValidationResult(is_valid=True)
