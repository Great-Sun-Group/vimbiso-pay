"""Base validator implementation with common validation logic"""
from typing import Dict, Any, Set
from .validator_interface import FlowValidatorInterface, ValidationResult


class BaseFlowValidator(FlowValidatorInterface):
    """Base validator with common validation logic"""

    def validate_flow_data(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate flow data structure"""
        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Check required flow fields
        required_fields = {"id", "step", "data"}
        missing = required_fields - set(flow_data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required flow fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate step is a non-negative integer
        if not isinstance(flow_data["step"], int) or flow_data["step"] < 0:
            return ValidationResult(
                is_valid=False,
                error_message="Step must be a non-negative integer"
            )

        # Validate flow data
        data = flow_data.get("data", {})
        if not isinstance(data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Validate required data fields
        required_data_fields = {
            "channel",  # Channel info required instead of mobile_number
            "member_id",
            "account_id",
            "flow_type",
            "_validation_context",
            "_validation_state"
        }
        missing_data = required_data_fields - set(data.keys())
        if missing_data:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required flow data fields: {', '.join(missing_data)}",
                missing_fields=missing_data
            )

        # Validate channel structure
        channel = data.get("channel", {})
        if not isinstance(channel, dict) or not all(k in channel for k in ["type", "identifier"]):
            return ValidationResult(
                is_valid=False,
                error_message="Channel must be a dictionary with 'type' and 'identifier' fields"
            )

        # Validate validation context is a dictionary
        if not isinstance(data["_validation_context"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Validation context must be a dictionary"
            )

        # Validate validation state is a dictionary
        if not isinstance(data["_validation_state"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Validation state must be a dictionary"
            )

        return ValidationResult(is_valid=True)

    def validate_flow_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete flow state"""
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Check required fields
        required_fields = self.get_required_fields()
        missing = required_fields - set(state.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required state fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate flow data if present
        if "flow_data" in state:
            flow_validation = self.validate_flow_data(state["flow_data"])
            if not flow_validation.is_valid:
                return flow_validation

        return ValidationResult(is_valid=True)

    def get_required_fields(self) -> Set[str]:
        """Get base required fields"""
        return {
            "channel",  # Channel info required instead of mobile_number
            "member_id",
            "account_id",
            "_validation_context",
            "_validation_state"
        }
