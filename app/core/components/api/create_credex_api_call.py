"""Create Credex API call component

This component handles creating a new Credex offer through the API.
Dashboard data is the source of truth for member state.
"""

from typing import Any, Dict

from decouple import config

from core.utils.error_types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent


class CreateCredexApiCall(ApiComponent):
    """Handles creating a new Credex offer"""

    def __init__(self):
        super().__init__("create_credex_api")
        self.state_manager = None
        self.bot_service = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def set_bot_service(self, bot_service: Any) -> None:
        """Set bot service for API access"""
        self.bot_service = bot_service

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Call createCredex endpoint and validate response"""
        # Get member data from dashboard
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"component": "create_credex"}
            )

        member_id = dashboard.get("member", {}).get("memberID")
        if not member_id:
            return ValidationResult.failure(
                message="No member ID found in dashboard",
                field="member_id",
                details={"component": "create_credex"}
            )

        # Get active account ID from state
        active_account_id = self.state_manager.get("active_account_id")
        if not active_account_id:
            return ValidationResult.failure(
                message="No active account selected",
                field="active_account",
                details={"component": "create_credex"}
            )

        # Get offer details from flow data
        flow_data = self.state_manager.get_flow_state()
        if not flow_data or "data" not in flow_data:
            return ValidationResult.failure(
                message="No offer data found",
                field="flow_data",
                details={"component": "create_credex"}
            )

        # Get offer details
        offer_data = flow_data["data"]
        amount = offer_data.get("amount")
        handle = offer_data.get("handle")

        if not amount or not handle:
            return ValidationResult.failure(
                message="Missing required offer fields",
                field="offer_data",
                details={
                    "missing_fields": [
                        "amount" if not amount else None,
                        "handle" if not handle else None
                    ]
                }
            )

        # Make API call
        url = f"createCredex/{member_id}/{active_account_id}"
        headers = {
            "Content-Type": "application/json",
            "x-client-api-key": config("CLIENT_API_KEY"),
        }
        payload = {
            "amount": amount,
            "handle": handle
        }

        response = make_api_request(url, headers, payload)

        # Let handlers update state
        response_data, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )
        if error:
            return ValidationResult.failure(
                message=f"Failed to create Credex: {error}",
                field="api_call",
                details={"error": error}
            )

        # Get action data for flow
        flow_data = self.state_manager.get_flow_state()
        action_data = flow_data.get("action", {})

        return ValidationResult.success({
            "action": action_data,
            "credex_created": True
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Most data is in dashboard state, we just need
        success indicators and action details here.
        """
        return {
            "credex_created": True,
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }