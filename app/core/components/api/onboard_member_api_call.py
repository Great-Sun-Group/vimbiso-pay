"""Onboard member API call component

Handles member registration:
- Gets registration data from component_data.data (unvalidated)
- Creates new member account via API
- Updates state with schema-validated dashboard data
"""

from typing import Any, Dict

from core.api.base import handle_api_response, make_api_request
from core.error.types import ValidationResult

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
        component_data = self.state_manager.get_state_value("component_data", {})
        registration_data = component_data.get("data", {})
        if not registration_data:
            return ValidationResult.failure(
                message="No registration data found",
                field="component_data.data",
                details={"component": self.type}
            )
        firstname = registration_data.get("firstname")
        lastname = registration_data.get("lastname")

        # Validate required fields
        if not firstname or not lastname:
            return ValidationResult.failure(
                message="Missing required registration data",
                field="registration_data",
                details={
                    "component": self.type,
                    "firstname": firstname,
                    "lastname": lastname
                }
            )

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
        payload = {
            "firstname": firstname,
            "lastname": lastname,
            "phone": channel["identifier"],
            "defaultDenom": "USD"  # Default denomination required by API
        }

        # Make request and store response
        response = make_api_request(
            url=url,
            payload=payload,
            state_manager=self.state_manager
        )

        # Store response data in state
        response_data, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )

        # Validate response has required data
        if not response_data.get("data", {}).get("dashboard", {}).get("member", {}).get("memberID"):
            return ValidationResult.failure(
                message="Registration failed: Invalid response data",
                field="api_call",
                details={"error": error or "No member ID in response"}
            )

        # Clear firstname/lastname from earlier components
        self.update_data({})

        # Set active_account_id to the personal account
        dashboard = response_data.get("data", {}).get("dashboard", {})
        accounts = dashboard.get("accounts", [])
        for account in accounts:
            if account.get("accountType") == "PERSONAL":
                self.state_manager.update_state({
                    "active_account_id": account["accountID"]
                })
                break

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
