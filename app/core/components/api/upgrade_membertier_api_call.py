"""Upgrade member tier API call component

This component handles the upgrade member tier API call with proper validation.
Dashboard data is the source of truth for member state.
"""

from typing import Any, Dict

from decouple import config

from core.utils.error_types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent


class UpgradeMembertierApiCall(ApiComponent):
    """Handles upgrade member tier API call"""

    def __init__(self):
        super().__init__("upgrade_membertier_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing member data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Call upgradeMemberTier endpoint and validate response"""
        # Get dashboard data from state
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"component": "upgrade_membertier"}
            )

        # Get member ID from dashboard
        member_id = dashboard.get("member", {}).get("memberID")
        if not member_id:
            return ValidationResult.failure(
                message="No member ID found in dashboard",
                field="member_id",
                details={"component": "upgrade_membertier"}
            )

        # Make API call
        url = f"upgradeMemberTier/{member_id}"
        headers = {
            "Content-Type": "application/json",
            "x-client-api-key": config("CLIENT_API_KEY"),
        }

        response = make_api_request(url, headers, {})

        # Let handlers update state
        response_data, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )
        if error:
            return ValidationResult.failure(
                message=f"Upgrade failed: {error}",
                field="api_call",
                details={"error": error}
            )

        # Get action data from component data
        component_data = self.state_manager.get_component_data()
        action_data = component_data.get("action", {})

        return ValidationResult.success({
            "action": action_data,
            "upgraded": True
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert upgrade response to verified data

        Note: Member data is in dashboard state, we just need
        upgrade status and action details here.
        """
        return {
            "upgrade_complete": True,
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
