"""Accept offer API call component

This component handles accepting a Credex offer through the API.
Dashboard data is the source of truth for member state.
"""

from typing import Any, Dict

from decouple import config

from core.error.types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent


class AcceptOfferApiCall(ApiComponent):
    """Handles accepting a Credex offer"""

    def __init__(self):
        super().__init__("accept_offer_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Call acceptOffer endpoint and validate response"""
        # Get member data from dashboard
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"component": "accept_offer"}
            )

        member_id = dashboard.get("member", {}).get("memberID")
        if not member_id:
            return ValidationResult.failure(
                message="No member ID found in dashboard",
                field="member_id",
                details={"component": "accept_offer"}
            )

        # Get active account ID from state
        active_account_id = self.state_manager.get("active_account_id")
        if not active_account_id:
            return ValidationResult.failure(
                message="No active account selected",
                field="active_account",
                details={"component": "accept_offer"}
            )

        # Get selected offer from component data
        offer_data = self.state_manager.get_component_data()
        if not offer_data:
            return ValidationResult.failure(
                message="No offer data found",
                field="component_data",
                details={"component": "accept_offer"}
            )
        credex_id = offer_data.get("credex_id")
        if not credex_id:
            return ValidationResult.failure(
                message="No Credex ID found",
                field="credex_id",
                details={"component": "accept_offer"}
            )

        # Make API call
        url = f"acceptOffer/{member_id}/{active_account_id}/{credex_id}"
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
                message=f"Failed to accept offer: {error}",
                field="api_call",
                details={"error": error}
            )

        # Get action data from component data
        component_data = self.state_manager.get_component_data()
        action_data = component_data.get("action", {})

        return ValidationResult.success({
            "action": action_data,
            "offer_accepted": True
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Most data is in dashboard state, we just need
        success indicators and action details here.
        """
        return {
            "offer_accepted": True,
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
