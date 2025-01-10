"""Get ledger API call component

This component handles retrieving account ledger data through the API.
Dashboard data is the source of truth for member state.
"""

from typing import Any, Dict

from decouple import config

from core.utils.error_types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent


class GetLedgerApiCall(ApiComponent):
    """Handles retrieving account ledger data"""

    def __init__(self):
        super().__init__("get_ledger_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing ledger data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Call getLedger endpoint and validate response"""
        # Get member data from dashboard
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"component": "get_ledger"}
            )

        member_id = dashboard.get("member", {}).get("memberID")
        if not member_id:
            return ValidationResult.failure(
                message="No member ID found in dashboard",
                field="member_id",
                details={"component": "get_ledger"}
            )

        # Get active account ID from state
        active_account_id = self.state_manager.get("active_account_id")
        if not active_account_id:
            return ValidationResult.failure(
                message="No active account selected",
                field="active_account",
                details={"component": "get_ledger"}
            )

        # Make API call
        url = f"getLedger/{member_id}/{active_account_id}"
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
                message=f"Failed to get ledger: {error}",
                field="api_call",
                details={"error": error}
            )

        # Get action data from component data
        component_data = self.state_manager.get_component_data()
        action_data = component_data.get("action", {})

        return ValidationResult.success({
            "action": action_data,
            "entries": response_data.get("data", {}).get("entries", []),
            "total_pages": response_data.get("data", {}).get("totalPages", 1),
            "current_page": response_data.get("data", {}).get("currentPage", 1)
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Most data is in dashboard state, we just need
        ledger data and action details here.
        """
        return {
            "entries": value.get("entries", []),
            "total_pages": value.get("totalPages", 1),
            "current_page": value.get("currentPage", 1),
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
