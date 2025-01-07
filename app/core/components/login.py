"""Login components

This module provides components for handling login flows with pure UI validation.
Business validation happens in services.
"""

from typing import Any, Dict

from core.utils.error_types import ValidationResult

from .base import Component


class LoginApiCall(Component):
    """Handles login API call with proper exit conditions"""

    def __init__(self):
        super().__init__("login")
        self.state_manager = None
        self.bot_service = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing state data"""
        self.state_manager = state_manager

    def set_bot_service(self, bot_service: Any) -> None:
        """Set bot service for API access"""
        self.bot_service = bot_service

    def validate(self, value: Any) -> ValidationResult:
        """Call login endpoint and validate response"""
        # Validate state manager and bot service are set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "login"}
            )

        if not self.bot_service:
            return ValidationResult.failure(
                message="Bot service not set",
                field="bot_service",
                details={"component": "login"}
            )

        # Call login endpoint
        from core.api.login import login
        success, message = login(self.bot_service)

        if success:
            # Get API response from state
            flow_data = self.state_manager.get_flow_state()
            if not flow_data or "data" not in flow_data:
                return ValidationResult.failure(
                    message="No state data after login",
                    field="flow_data",
                    details={"component": "login"}
                )

            # Return success with exit condition
            return ValidationResult.success(
                flow_data["data"],
                metadata={
                    "exit_condition": "success"  # Exit to dashboard
                }
            )
        elif "Welcome!" in message:
            # New user - proceed to onboarding
            return ValidationResult.success(
                {"message": message},
                metadata={
                    "exit_condition": "not_member"  # Exit to onboarding
                }
            )
        else:
            # Login error
            return ValidationResult.failure(
                message=message,
                field="login",
                details={
                    "error": message,
                    "component": "login"
                }
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data"""
        return {
            "message": value.get("message", ""),
            "authenticated": "message" not in value  # True if we got API data, False if just welcome message
        }
