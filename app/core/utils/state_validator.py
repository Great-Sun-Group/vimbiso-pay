"""Core state validation enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict

from .validator_interface import ValidationResult


class StateValidator:
    """Validates core state structure focusing on SINGLE SOURCE OF TRUTH"""

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate state structure enforcing SINGLE SOURCE OF TRUTH"""
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate channel structure (required)
        if "channel" not in state or not isinstance(state["channel"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Channel info must be present as dictionary"
            )

        # Validate channel has required fields
        channel = state["channel"]
        for field in ["type", "identifier"]:
            if field not in channel:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Channel missing required field: {field}"
                )
            if not isinstance(channel[field], (str, type(None))):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Channel {field} must be string or None"
                )

        # Validate channel metadata
        if "metadata" not in channel:
            channel["metadata"] = {}
        elif not isinstance(channel["metadata"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Channel metadata must be a dictionary"
            )

        # Validate member_id if present (SINGLE SOURCE OF TRUTH)
        if "member_id" in state and not isinstance(state["member_id"], (str, type(None))):
            return ValidationResult(
                is_valid=False,
                error_message="Member ID must be string or None"
            )

        # Validate jwt_token if present (SINGLE SOURCE OF TRUTH)
        if "jwt_token" in state and not isinstance(state["jwt_token"], (str, type(None))):
            return ValidationResult(
                is_valid=False,
                error_message="JWT token must be string or None"
            )

        # Validate flow_data if present
        if "flow_data" in state and not isinstance(state["flow_data"], (dict, type(None))):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be dictionary or None"
            )

        return ValidationResult(is_valid=True)
