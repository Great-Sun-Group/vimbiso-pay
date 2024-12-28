"""Core state validation enforcing SINGLE SOURCE OF TRUTH"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set


@dataclass
class ValidationResult:
    """Result of state validation"""
    is_valid: bool
    error_message: Optional[str] = None


class StateValidator:
    """Validates core state structure focusing on SINGLE SOURCE OF TRUTH"""

    # Critical fields that must be validated
    CRITICAL_FIELDS = {
        "channel"  # Only channel is required for new users
    }

    # Fields that must never be duplicated
    UNIQUE_FIELDS = {
        "member_id",
        "channel"
    }

    # Fields that must exist but can be None
    NULLABLE_FIELDS = {
        "member_id",
        "jwt_token",
        "authenticated",
        "flow_data",
        "account_id"
    }

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate state structure enforcing SINGLE SOURCE OF TRUTH"""
        # Validate state is dictionary
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate critical fields exist and are not None
        missing_fields = cls.CRITICAL_FIELDS - set(state.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing critical fields: {', '.join(missing_fields)}"
            )

        # Validate channel structure (required)
        channel_validation = cls._validate_channel(state.get("channel"))
        if not channel_validation.is_valid:
            return channel_validation

        # Validate nullable fields if present
        for field in cls.NULLABLE_FIELDS:
            if field in state and not isinstance(state[field], (str, type(None), bool, dict)):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field} must be string, None, boolean or dict"
                )

        # Validate flow_data structure if present
        if "flow_data" in state:
            flow_validation = cls._validate_flow_data(state["flow_data"])
            if not flow_validation.is_valid:
                return flow_validation

        # Validate no state duplication
        duplication_validation = cls._validate_no_duplication(state)
        if not duplication_validation.is_valid:
            return duplication_validation

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_channel(cls, channel: Any) -> ValidationResult:
        """Validate channel structure"""
        if not isinstance(channel, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Channel must be a dictionary"
            )

        # Required channel fields
        required_fields = {"type", "identifier"}
        missing_fields = required_fields - set(channel.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Channel missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(channel["type"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Channel type must be string"
            )

        if not isinstance(channel["identifier"], (str, type(None))):
            return ValidationResult(
                is_valid=False,
                error_message="Channel identifier must be string or None"
            )

        # Validate metadata if present
        if "metadata" in channel:
            if not isinstance(channel["metadata"], dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel metadata must be a dictionary"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_flow_data(cls, flow_data: Any) -> ValidationResult:
        """Validate flow data structure"""
        # Allow empty dict for initial state
        if flow_data == {}:
            return ValidationResult(is_valid=True)

        # Must be a dictionary
        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="flow_data must be a dictionary"
            )

        # Validate required fields
        required_fields = {"flow_type", "step", "current_step"}
        missing_fields = required_fields - set(flow_data.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"flow_data missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(flow_data["flow_type"], str):
            return ValidationResult(
                is_valid=False,
                error_message="flow_type must be string"
            )

        if not isinstance(flow_data["step"], int):
            return ValidationResult(
                is_valid=False,
                error_message="step must be integer"
            )

        if not isinstance(flow_data["current_step"], str):
            return ValidationResult(
                is_valid=False,
                error_message="current_step must be string"
            )

        # Validate data field if present
        if "data" in flow_data:
            if not isinstance(flow_data["data"], dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="flow_data.data must be a dictionary"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_no_duplication(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate no state duplication"""
        # Check for nested member_id
        if any(isinstance(v, dict) and "member_id" in v for v in state.values()):
            return ValidationResult(
                is_valid=False,
                error_message="member_id found in nested state - must only exist at top level"
            )

        # Check for nested channel info
        if any(isinstance(v, dict) and "channel" in v for v in state.values()):
            return ValidationResult(
                is_valid=False,
                error_message="channel info found in nested state - must only exist at top level"
            )

        # Check for state passing in flow data
        if "flow_data" in state and isinstance(state["flow_data"], dict):
            for field in cls.UNIQUE_FIELDS:
                if field in state["flow_data"]:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"{field} found in flow data - must not be passed between components"
                    )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_before_access(cls, state: Dict[str, Any], required_fields: Set[str]) -> ValidationResult:
        """Validate state before accessing specific fields"""
        # Validate state is dictionary
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate critical fields if being accessed
        critical_required = required_fields & cls.CRITICAL_FIELDS
        if critical_required:
            missing_critical = critical_required - set(state.keys())
            if missing_critical:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing critical fields: {', '.join(missing_critical)}"
                )

            # Validate channel structure if required
            if "channel" in critical_required:
                channel_validation = cls._validate_channel(state.get("channel"))
                if not channel_validation.is_valid:
                    return channel_validation

        # Validate types of any nullable fields being accessed
        nullable_accessed = required_fields & cls.NULLABLE_FIELDS
        for field in nullable_accessed:
            if field in state:
                if field == "flow_data":
                    # Validate flow data structure when accessed
                    flow_validation = cls._validate_flow_data(state[field])
                    if not flow_validation.is_valid:
                        return flow_validation
                elif not isinstance(state[field], (str, type(None), bool, dict)):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"{field} must be string, None, boolean or dict"
                    )

        # Check for duplication only in accessed fields
        unique_accessed = required_fields & cls.UNIQUE_FIELDS
        for field in unique_accessed:
            if any(isinstance(v, dict) and field in v for v in state.values()):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field} found in nested state - must only exist at top level"
                )

        return ValidationResult(is_valid=True)
