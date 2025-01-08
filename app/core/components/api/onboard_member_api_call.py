"""Onboard member API call component

This component handles the onboard member API call with proper validation.
Dashboard data is the source of truth for member state.
"""

from typing import Any, Dict

from decouple import config

from core.utils.error_types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent


class OnBoardMemberApiCall(ApiComponent):
    """Handles onboarding API call with proper exit conditions"""

    def __init__(self):
        super().__init__("onboard_member_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing member data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Call onboardMember endpoint and validate response"""
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
        firstname = registration_data.get("firstname")
        lastname = registration_data.get("lastname")

        # Get channel info from state manager
        channel = self.state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            return ValidationResult.failure(
                message="No channel identifier found",
                field="channel",
                details={"component": "onboard_member"}
            )

        # Make API call
        url = "onboardMember"
        headers = {
            "Content-Type": "application/json",
            "x-client-api-key": config("CLIENT_API_KEY"),
        }
        payload = {
            "firstname": firstname,
            "lastname": lastname,
            "phone": channel["identifier"],
            "defaultDenom": "USD"  # Default denomination required by API
        }

        response = make_api_request(url, headers, payload)

        # Let handlers update state
        response_data, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )
        if error:
            return ValidationResult.failure(
                message=f"Registration failed: {error}",
                field="api_call",
                details={"error": error}
            )

        # Get action data for flow
        flow_data = self.state_manager.get_flow_state()
        action_data = flow_data.get("action", {})

        return ValidationResult.success({
            "action": action_data,
            "registered": True
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert registration data to verified data

        Note: Most data is in dashboard state, we just need
        success indicators and action details here.
        """
        return {
            "authenticated": True,
            "registered": True,
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
