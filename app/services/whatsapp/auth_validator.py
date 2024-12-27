"""Validator for authentication flows enforcing SINGLE SOURCE OF TRUTH"""
from typing import Dict, Any, Set
from core.utils.validator_interface import FlowValidatorInterface, ValidationResult
from core.utils.state_validator import StateValidator


class AuthFlowValidator(FlowValidatorInterface):
    """Validator for authentication flows with strict state validation"""

    def validate_before_access(self, state: Dict[str, Any], fields: Set[str]) -> ValidationResult:
        """Validate state before access enforcing SINGLE SOURCE OF TRUTH

        Args:
            state: State to validate
            fields: Fields being accessed

        Returns:
            ValidationResult: Validation result with error details if invalid

        Rules:
        - Must validate fields before access
        - Must check for required fields
        - Must prevent state duplication
        - Must enforce single source of truth
        """
        try:
            # Validate input types
            if not isinstance(state, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="State must be a dictionary"
                )
            if not isinstance(fields, set):
                return ValidationResult(
                    is_valid=False,
                    error_message="Fields must be a set"
                )

            # Check for required fields
            missing = fields - set(state.keys())
            if missing:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required fields: {', '.join(missing)}",
                    missing_fields=missing
                )

            # Check for state duplication in critical fields
            for field in self.UNIQUE_FIELDS & fields:
                value = state.get(field)
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, dict) and field in nested_value:
                            return ValidationResult(
                                is_valid=False,
                                error_message=f"{field} found in nested state - must only exist at top level"
                            )

            # Validate channel structure if being accessed
            if "channel" in fields:
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

            return ValidationResult(is_valid=True)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )

    # Critical fields that must be validated
    CRITICAL_FIELDS = {
        "member_id",
        "channel",
        "jwt_token"
    }

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
