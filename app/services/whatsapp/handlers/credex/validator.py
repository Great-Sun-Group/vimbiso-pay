"""Validator for credex flow states"""
from typing import Dict, Any, Set
from core.utils.validator_interface import ValidationResult
from core.utils.state_validator import StateValidator
from core.utils.base_validator import BaseFlowValidator


class CredexFlowValidator(BaseFlowValidator):
    """Validator for credex flow states"""

    def validate_flow_data(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate credex flow data structure"""
        # First validate using base validator
        base_validation = super().validate_flow_data(flow_data)
        if not base_validation.is_valid:
            return base_validation

        # Extract flow type from ID
        flow_id = flow_data["id"]
        flow_type = flow_id.split("_")[0] if "_" in flow_id else flow_id

        # Get data for flow-specific validation
        data = flow_data["data"]

        # Validate data based on flow type
        if flow_type == "offer":
            return self._validate_offer_data(data)
        elif flow_type == "cancel":
            return self._validate_cancel_data(data)
        elif flow_type in {"accept", "decline"}:
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
        # For list selection step, only require basic fields
        basic_fields = {"mobile_number", "member_id"}
        missing_basic = basic_fields - set(data.keys())
        if missing_basic:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing basic data fields: {', '.join(missing_basic)}",
                missing_fields=missing_basic
            )

        # For confirmation step, require credex_id
        if "credex_id" not in data and data.get("step", 0) > 0:
            return ValidationResult(
                is_valid=False,
                error_message="Missing credex_id for confirmation",
                missing_fields={"credex_id"}
            )

        return ValidationResult(is_valid=True)

    def _validate_action_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate accept/decline-specific data"""
        # For list selection step, only require basic fields
        basic_fields = {"mobile_number", "member_id"}
        missing_basic = basic_fields - set(data.keys())
        if missing_basic:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing basic data fields: {', '.join(missing_basic)}",
                missing_fields=missing_basic
            )

        # For confirmation step, require credex_id
        if "credex_id" not in data and data.get("step", 0) > 0:
            return ValidationResult(
                is_valid=False,
                error_message="Missing credex_id for confirmation",
                missing_fields={"credex_id"}
            )

        return ValidationResult(is_valid=True)
