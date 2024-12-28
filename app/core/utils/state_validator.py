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

    # Required fields that can't be modified
    CRITICAL_FIELDS = {"channel"}

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate state structure enforcing SINGLE SOURCE OF TRUTH"""
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

        channel_validation = cls._validate_channel(state["channel"])
        if not channel_validation.is_valid:
            return channel_validation

        # Validate flow_data structure if present
        if "flow_data" in state:
            flow_validation = cls._validate_flow_data(state["flow_data"])
            if not flow_validation.is_valid:
                return flow_validation

        # Only validate auth for non-null member/account operations
        if (state.get("member_id") is not None or state.get("account_id") is not None):
            if not state.get("authenticated"):
                return ValidationResult(
                    is_valid=False,
                    error_message="Authentication required for member operations"
                )
            if not state.get("jwt_token"):
                return ValidationResult(
                    is_valid=False,
                    error_message="Valid token required for member operations"
                )

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
        # Must be a dictionary
        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="flow_data must be a dictionary"
            )

        # Allow empty dict for initial state only
        if flow_data == {}:
            return ValidationResult(is_valid=True)

        # Require all flow fields if any data or flow fields are present
        flow_fields = {"flow_type", "step", "current_step"}
        if "data" in flow_data or any(field in flow_data for field in flow_fields):
            # Check all required fields exist
            missing_fields = flow_fields - set(flow_data.keys())
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
    def validate_before_access(cls, state: Dict[str, Any], required_fields: Set[str]) -> ValidationResult:
        """Validate state before accessing specific fields"""
        # Validate state is dictionary
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate channel if required
        if "channel" in required_fields:
            if "channel" not in state:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required field: channel"
                )
            channel_validation = cls._validate_channel(state["channel"])
            if not channel_validation.is_valid:
                return channel_validation

        # Only validate auth for non-null member/account access
        if ("member_id" in required_fields and state.get("member_id") is not None or "account_id" in required_fields and state.get("account_id") is not None):
            if not state.get("authenticated"):
                return ValidationResult(
                    is_valid=False,
                    error_message="Authentication required for member operations"
                )
            if not state.get("jwt_token"):
                return ValidationResult(
                    is_valid=False,
                    error_message="Valid token required for member operations"
                )

        # Validate flow_data structure if being accessed
        if "flow_data" in required_fields and "flow_data" in state:
            flow_validation = cls._validate_flow_data(state["flow_data"])
            if not flow_validation.is_valid:
                return flow_validation

        return ValidationResult(is_valid=True)
