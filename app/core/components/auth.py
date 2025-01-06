"""Authentication components

This module provides components for handling authentication flows with pure UI validation.
Business validation happens in services.
"""

from typing import Any, Dict

from core.utils.error_types import ValidationResult

from .base import InputComponent


class LoginHandler(InputComponent):
    """Handles login attempts with pure UI validation"""

    def __init__(self):
        super().__init__("login")

    def validate(self, value: Any) -> ValidationResult:
        """No validation needed - component is self-sufficient"""
        return ValidationResult.success({})

    def to_verified_data(self, value: Any) -> Dict:
        """No data needed - component handles login internally"""
        return {
            "action": "login"
        }


class LoginCompleteHandler(InputComponent):
    """Handles successful login completion with pure UI validation"""

    def __init__(self):
        super().__init__("login_complete")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing dashboard data"""
        self.state_manager = state_manager

    def validate(self, value: Any) -> ValidationResult:
        """Validate login response with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, dict, "object")
        if not type_result.valid:
            return type_result

        # Validate required fields
        required = {"member_id", "token"}
        missing = required - set(value.keys())
        if missing:
            return ValidationResult.failure(
                message="Missing required login fields",
                field="response",
                details={
                    "missing_fields": list(missing),
                    "received_fields": list(value.keys())
                }
            )

        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "login_complete"}
            )

        return ValidationResult.success(value)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert login response to verified data"""
        return {
            "member_id": value["member_id"],
            "jwt_token": value["token"],
            "authenticated": True
        }
