"""Validator for authentication flows enforcing SINGLE SOURCE OF TRUTH"""
from typing import Dict, Any, Set
from core.utils.validator_interface import FlowValidatorInterface, ValidationResult
from core.utils.state_validator import StateValidator


class AuthFlowValidator(FlowValidatorInterface):
    """Validator for authentication flows with strict state validation"""

    # Critical fields that must be validated
    CRITICAL_FIELDS = {
        "member_id",
        "channel",
        "jwt_token"
    }

    # Fields that must never be duplicated
    UNIQUE_FIELDS = {
        "member_id",
        "channel"
    }

    # Required fields for authenticated state
    AUTH_FIELDS = {
        "member_id",    # Primary identifier (SINGLE SOURCE OF TRUTH)
        "jwt_token",    # Authentication token
        "channel",      # Channel information (SINGLE SOURCE OF TRUTH)
        "account_id",   # Current account ID
        "authenticated"     # Authentication state
    }

    def validate_flow_data(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate auth flow data structure

        Args:
            flow_data: Flow data to validate

        Returns:
            ValidationResult: Validation result with error details if invalid

        Rules:
        - Must be None or a dictionary
        - If dictionary, must have id and step fields
        - Step must be a non-negative integer
        - Must not contain any critical state fields
        """
        # Allow None for flow_data when clearing flow
        if flow_data is None:
            return ValidationResult(is_valid=True)

        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Empty flow data is valid for initial state
        if not flow_data:
            return ValidationResult(is_valid=True)

        # Check for state duplication
        for field in self.UNIQUE_FIELDS:
            if field in flow_data:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field} found in flow data - must not be passed between components"
                )

        required_fields = {"id", "step"}
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
                error_message="Step must be a non-negative integer"
            )

        return ValidationResult(is_valid=True)

    def validate_flow_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete flow state

        Args:
            state: State to validate

        Returns:
            ValidationResult: Validation result with error details if invalid

        Rules:
        - Must pass core state validation
        - Must have required auth fields if authenticated
        - Must not have duplicated state
        - Must not have nested state
        - Flow data must be valid if present
        """
        # First validate core state structure
        core_validation = StateValidator.validate_state(state)
        if not core_validation.is_valid:
            return core_validation

        # Check for state duplication
        for field in self.UNIQUE_FIELDS:
            for value in state.values():
                if isinstance(value, dict) and field in value:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"{field} found in nested state - must only exist at top level"
                    )

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
            auth_fields = self.AUTH_FIELDS
            missing_auth = auth_fields - set(state.keys())
            if missing_auth:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing authenticated state fields: {', '.join(missing_auth)}",
                    missing_fields=missing_auth
                )

        # Validate flow data if present and not None
        if "flow_data" in state and state["flow_data"] is not None:
            flow_validation = self.validate_flow_data(state["flow_data"])
            if not flow_validation.is_valid:
                return flow_validation

        return ValidationResult(is_valid=True)

    def get_required_fields(self) -> Set[str]:
        """Get required fields for auth flows"""
        return {"channel"}  # Channel info is required for all auth flows

    def validate_login_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate login state specifically

        Args:
            state: State to validate

        Returns:
            ValidationResult: Validation result with error details if invalid

        Rules:
        - Must pass basic flow state validation
        - Must have all required login fields if authenticated
        - Channel must be properly structured
        - Must not have duplicated state
        - Must not have nested state
        """
        # First validate basic state
        basic_validation = self.validate_flow_state(state)
        if not basic_validation.is_valid:
            return basic_validation

        # Additional login state validation
        if state.get("authenticated"):
            # Check required fields
            missing = self.AUTH_FIELDS - set(state.keys())
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

            # Validate channel field types
            if not isinstance(channel["type"], str):
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel type must be a string"
                )
            if not isinstance(channel["identifier"], (str, type(None))):
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel identifier must be string or None"
                )

        return ValidationResult(is_valid=True)
