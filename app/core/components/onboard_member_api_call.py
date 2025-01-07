"""Onboard member API call component

This component handles the onboard member API call with proper validation.
Dashboard data is the source of truth for member state.
"""

from typing import Any, Dict

from core.utils.error_types import ValidationResult

from .base import Component


class OnBoardMemberApiCall(Component):
    """Handles onboarding API call with proper exit conditions"""

    def __init__(self):
        super().__init__("onboard_member_api")
        self.state_manager = None
        self.bot_service = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing registration data"""
        self.state_manager = state_manager

    def set_bot_service(self, bot_service: Any) -> None:
        """Set bot service for API access"""
        self.bot_service = bot_service

    def validate(self, value: Any) -> ValidationResult:
        """Call onboardMember endpoint and validate response"""
        # Validate state manager and bot service are set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "onboard_member"}
            )

        if not self.bot_service:
            return ValidationResult.failure(
                message="Bot service not set",
                field="bot_service",
                details={"component": "onboard_member"}
            )

        # Get registration data from state
        flow_data = self.state_manager.get_flow_state()
        if not flow_data or "data" not in flow_data:
            return ValidationResult.failure(
                message="No registration data found",
                field="flow_data",
                details={"component": "onboard_member"}
            )

        # Get registration data
        registration_data = flow_data["data"]

        # Get channel info from state manager
        channel = self.state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            return ValidationResult.failure(
                message="No channel identifier found",
                field="channel",
                details={"component": "onboard_member"}
            )

        member_data = {
            "firstname": registration_data.get("firstname"),
            "lastname": registration_data.get("lastname"),
            "phone": channel["identifier"],
            "defaultDenom": "USD"  # Default denomination required by API
        }

        # Call onboardMember endpoint
        from core.api.login import onboard_member
        success, response = onboard_member(
            bot_service=self.bot_service,
            member_data=member_data
        )

        if not success:
            return ValidationResult.failure(
                message=f"Registration failed: {response.get('message')}",
                field="api_call",
                details={"error": response}
            )

        # Get dashboard data from state
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data after registration",
                field="dashboard",
                details={"component": "onboard_member"}
            )

        # Dashboard data is our source of truth
        return ValidationResult.success({
            "registered": True,
            "dashboard": dashboard
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert registration data to verified data

        Note: Most data is now in dashboard state, we just need
        to return success indicators here.
        """
        return {
            "authenticated": True,
            "registered": True
        }
