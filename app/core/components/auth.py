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
        """Validate login attempt with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate greeting format
        greeting = value.strip().lower()
        if greeting not in ["hi", "hello"]:
            return ValidationResult.failure(
                message="Please start with a greeting (hi/hello)",
                field="greeting",
                details={
                    "valid_values": ["hi", "hello"],
                    "received": greeting
                }
            )

        return ValidationResult.success(greeting)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified login data"""
        return {
            "greeting": value.strip().lower(),
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
