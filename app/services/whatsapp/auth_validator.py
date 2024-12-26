"""Validator for authentication flows"""
from typing import Dict, Any, Set
from core.utils.validator_interface import FlowValidatorInterface, ValidationResult
from core.utils.state_validator import StateValidator


class AuthFlowValidator(FlowValidatorInterface):
    """Validator for authentication flows"""

    def validate_flow_data(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate auth flow data structure"""
        # Allow None for flow_data when clearing flow
        if flow_data is None:
            return ValidationResult(is_valid=True)

        # Ensure validation context if flow_data is a dict
        if isinstance(flow_data, dict):
            flow_data = StateValidator.ensure_validation_context(flow_data)

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

        return ValidationResult(is_valid=True)

    def validate_flow_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete flow state"""
        # Ensure validation context is present
        state = StateValidator.ensure_validation_context(state)

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

        # Validate flow data if present and not None
        # Allow None as valid state when clearing flow
        if "flow_data" in state and state["flow_data"] is not None:
            flow_validation = self.validate_flow_data(state["flow_data"])
            if not flow_validation.is_valid:
                return flow_validation

        return ValidationResult(is_valid=True)

    def get_required_fields(self) -> Set[str]:
        """Get required fields for auth flows"""
        return {"channel"}  # Channel info is required instead of mobile_number

    def validate_login_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate login state specifically"""
        # Ensure validation context is present
        state = StateValidator.ensure_validation_context(state)

        # First validate basic state
        basic_validation = self.validate_flow_state(state)
        if not basic_validation.is_valid:
            return basic_validation

        # Additional login state validation
        if state.get("authenticated"):
            required_fields = {
                "member_id",    # Primary identifier
                "channel",      # Channel information
                "jwt_token",    # Authentication
                "account_id",   # Account reference
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

            # Validate channel structure
            channel = state.get("channel", {})
            if not isinstance(channel, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel must be a dictionary"
                )

            required_channel = {"type", "identifier"}
            missing_channel = required_channel - set(channel.keys())
            if missing_channel:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing channel fields: {', '.join(missing_channel)}",
                    missing_fields=missing_channel
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
