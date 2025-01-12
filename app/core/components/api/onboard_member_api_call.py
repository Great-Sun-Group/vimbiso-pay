"""Onboard member API call component

Handles member registration:
- Gets registration data from component_data.data (unvalidated)
- Creates new member account via API
- Updates state with schema-validated dashboard data
"""

from typing import Any, Dict

from decouple import config

from core.error.types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent


class OnBoardMemberApiCall(ApiComponent):
    """Processes member registration and manages state"""

    def __init__(self):
        super().__init__("onboard_member_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing member data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process registration and update state

        - Gets registration data (firstname, lastname) from flow state
        - Creates new member account via API
        - Updates state with dashboard data via handle_api_response
        - Returns success status
        """
        # Get registration data from component data (components can store their own data in component_data.data)
        registration_data = self.state_manager.get_state_value("component_data", {})
        if not registration_data:
            return ValidationResult.failure(
                message="No registration data found",
                field="component_data",
                details={"component": self.type}
            )
        firstname = registration_data.get("firstname")
        lastname = registration_data.get("lastname")

        # Get channel info from state manager
        channel = self.state_manager.get_state_value("channel")
        if not channel or not channel.get("identifier"):
            return ValidationResult.failure(
                message="No channel identifier found",
                field="channel",
                details={"component": self.type}
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

        # Clear component_data.data since we've successfully consumed it
        self.update_component_data(data={})

        return ValidationResult.success({
            "status": "success",
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Dashboard/action data is handled by handle_api_response.
        We just track registration status here.
        """
        return {
            "registered": value.get("status") == "success"
        }
