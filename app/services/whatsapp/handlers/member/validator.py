"""Validator for member flow states"""
from typing import Dict, Any, Set
from core.utils.validator_interface import FlowValidatorInterface, ValidationResult
from core.utils.state_validator import StateValidator


class MemberFlowValidator(FlowValidatorInterface):
    """Validator for member flow states"""

    def validate_flow_data(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate member flow data structure"""
        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Empty flow data is valid for initial state
        if not flow_data:
            return ValidationResult(is_valid=True)

        required_fields = {"id", "step", "data"}
        missing = required_fields - set(flow_data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required flow fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate flow type
        if flow_data["id"] not in {"member_registration", "member_upgrade"}:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid member flow type"
            )

        # Validate step
        if not isinstance(flow_data["step"], int) or flow_data["step"] < 0:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid step value"
            )

        # Validate flow-specific data
        data = flow_data["data"]
        if not isinstance(data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Validate data based on flow type
        if flow_data["id"] == "member_registration":
            return self._validate_registration_data(data)
        elif flow_data["id"] == "member_upgrade":
            return self._validate_upgrade_data(data)

        return ValidationResult(is_valid=True)

    def validate_flow_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete flow state"""
        # First validate core state structure
        core_validation = StateValidator.validate_state(state)
        if not core_validation.is_valid:
            return core_validation

        # Check required fields for member flows
        missing = self.get_required_fields() - set(state.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing member flow fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate flow data if present
        if "flow_data" in state:
            return self.validate_flow_data(state["flow_data"])

        return ValidationResult(is_valid=True)

    def get_required_fields(self) -> Set[str]:
        """Get required fields for member flows"""
        return {"mobile_number"}

    def _validate_registration_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate registration-specific data"""
        required_fields = {"mobile_number", "phone"}
        missing = required_fields - set(data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing registration data fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate name data if present
        if "first_name" in data:
            first_name = data["first_name"]
            if not isinstance(first_name, dict) or "first_name" not in first_name:
                return ValidationResult(
                    is_valid=False,
                    error_message="Invalid first name data structure"
                )

        if "last_name" in data:
            last_name = data["last_name"]
            if not isinstance(last_name, dict) or "last_name" not in last_name:
                return ValidationResult(
                    is_valid=False,
                    error_message="Invalid last name data structure"
                )

        return ValidationResult(is_valid=True)

    def _validate_upgrade_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate upgrade-specific data"""
        required_fields = {"mobile_number", "account_id"}
        missing = required_fields - set(data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing upgrade data fields: {', '.join(missing)}",
                missing_fields=missing
            )

        return ValidationResult(is_valid=True)
