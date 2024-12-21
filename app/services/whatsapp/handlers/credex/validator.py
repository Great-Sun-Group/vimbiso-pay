"""Validator for credex flow states"""
from typing import Dict, Any, Set
from core.utils.validator_interface import FlowValidatorInterface, ValidationResult
from core.utils.state_validator import StateValidator


class CredexFlowValidator(FlowValidatorInterface):
    """Validator for credex flow states"""

    def validate_flow_data(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate credex flow data structure"""
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
        if flow_data["id"] not in {"credex_offer", "credex_cancel", "credex_accept", "credex_decline"}:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid credex flow type"
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
        if flow_data["id"] == "credex_offer":
            return self._validate_offer_data(data)
        elif flow_data["id"] == "credex_cancel":
            return self._validate_cancel_data(data)
        elif flow_data["id"] in {"credex_accept", "credex_decline"}:
            return self._validate_action_data(data)

        return ValidationResult(is_valid=True)

    def validate_flow_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete flow state"""
        # First validate core state structure
        core_validation = StateValidator.validate_state(state)
        if not core_validation.is_valid:
            return core_validation

        # Check required fields for credex flows
        missing = self.get_required_fields() - set(state.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing credex flow fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate flow data if present
        if "flow_data" in state:
            return self.validate_flow_data(state["flow_data"])

        return ValidationResult(is_valid=True)

    def get_required_fields(self) -> Set[str]:
        """Get required fields for credex flows"""
        return {"mobile_number", "member_id", "account_id"}

    def _validate_offer_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate offer-specific data"""
        required_fields = {"mobile_number", "member_id", "account_id"}
        missing = required_fields - set(data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing offer data fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate amount data if present
        if "amount_denom" in data:
            amount_data = data["amount_denom"]
            if not isinstance(amount_data, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Amount data must be a dictionary"
                )

            required_amount_fields = {"amount", "denomination"}
            missing_amount = required_amount_fields - set(amount_data.keys())
            if missing_amount:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing amount fields: {', '.join(missing_amount)}",
                    missing_fields=missing_amount
                )

        return ValidationResult(is_valid=True)

    def _validate_cancel_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate cancel-specific data"""
        required_fields = {"mobile_number", "member_id", "credex_id"}
        missing = required_fields - set(data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing cancel data fields: {', '.join(missing)}",
                missing_fields=missing
            )

        return ValidationResult(is_valid=True)

    def _validate_action_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate accept/decline-specific data"""
        required_fields = {"mobile_number", "member_id", "credex_id"}
        missing = required_fields - set(data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing action data fields: {', '.join(missing)}",
                missing_fields=missing
            )

        return ValidationResult(is_valid=True)
