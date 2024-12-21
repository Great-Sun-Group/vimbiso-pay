"""Validator for authentication flows"""
from typing import Dict, Any, Set
from core.utils.validator_interface import FlowValidatorInterface, ValidationResult
from core.utils.state_validator import StateValidator


class AuthFlowValidator(FlowValidatorInterface):
    """Validator for authentication flows"""

    def validate_flow_data(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate auth flow data structure"""
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
        if flow_data["id"] not in {"auth_login", "auth_register"}:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid auth flow type"
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
        if flow_data["id"] == "auth_login":
            return self._validate_login_data(data)
        elif flow_data["id"] == "auth_register":
            return self._validate_register_data(data)

        return ValidationResult(is_valid=True)

    def validate_flow_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete flow state"""
        # First validate core state structure
        core_validation = StateValidator.validate_state(state)
        if not core_validation.is_valid:
            return core_validation

        # Check required fields for auth flows
        missing = self.get_required_fields() - set(state.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing auth flow fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Additional validation for authenticated state
        if state.get("authenticated"):
            auth_fields = {"member_id", "account_id", "jwt_token"}
            missing_auth = auth_fields - set(state.keys())
            if missing_auth:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing authenticated state fields: {', '.join(missing_auth)}",
                    missing_fields=missing_auth
                )

        # Validate flow data if present
        if "flow_data" in state:
            return self.validate_flow_data(state["flow_data"])

        return ValidationResult(is_valid=True)

    def get_required_fields(self) -> Set[str]:
        """Get required fields for auth flows"""
        return {"mobile_number"}

    def _validate_login_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate login-specific data"""
        required_fields = {"mobile_number"}
        missing = required_fields - set(data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing login data fields: {', '.join(missing)}",
                missing_fields=missing
            )

        return ValidationResult(is_valid=True)

    def _validate_register_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate register-specific data"""
        required_fields = {"mobile_number"}
        missing = required_fields - set(data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing register data fields: {', '.join(missing)}",
                missing_fields=missing
            )

        return ValidationResult(is_valid=True)

    def validate_login_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate login state specifically"""
        # First validate basic state
        basic_validation = self.validate_flow_state(state)
        if not basic_validation.is_valid:
            return basic_validation

        # Additional login state validation
        if state.get("authenticated"):
            required_fields = {
                "jwt_token",
                "member_id",
                "account_id",
                "current_account",
                "profile"
            }
            missing = required_fields - set(state.keys())
            if missing:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing login state fields: {', '.join(missing)}",
                    missing_fields=missing
                )

            # Validate profile structure for login
            profile = state.get("profile", {})
            if not isinstance(profile, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Profile must be a dictionary"
                )

            # Validate dashboard data in profile
            dashboard = profile.get("dashboard")
            if not isinstance(dashboard, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Dashboard data must be a dictionary"
                )

            required_dashboard = {"member", "accounts"}
            missing_dashboard = required_dashboard - set(dashboard.keys())
            if missing_dashboard:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing dashboard fields: {', '.join(missing_dashboard)}",
                    missing_fields=missing_dashboard
                )

        return ValidationResult(is_valid=True)
