"""Get ledger API call component

Handles retrieving account ledger data through the API:
- Validates required data from state
- Makes API call to get ledger
- Updates state with response
- Sets component_result for flow control
"""

import logging
from typing import Any, Dict

from decouple import config

from core.error.types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent

logger = logging.getLogger(__name__)


class GetLedgerApiCall(ApiComponent):
    """Handles retrieving account ledger data and managing state"""

    def __init__(self):
        super().__init__("get_ledger_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing ledger data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process ledger retrieval and update state"""
        try:
            # Get member data from dashboard
            dashboard = self.state_manager.get_state_value("dashboard")
            if not dashboard:
                return ValidationResult.failure(
                    message="No dashboard data found",
                    field="dashboard",
                    details={"component": self.type}
                )

            member_id = dashboard.get("member", {}).get("memberID")
            if not member_id:
                return ValidationResult.failure(
                    message="No member ID found in dashboard",
                    field="member_id",
                    details={"component": self.type}
                )

            # Get active account ID from state
            active_account_id = self.state_manager.get_state_value("active_account_id")
            if not active_account_id:
                return ValidationResult.failure(
                    message="No active account selected",
                    field="active_account",
                    details={"component": self.type}
                )

            # Get pagination data if available
            component_data = self.state_manager.get_state_value("component_data", {})
            pagination = component_data.get("data", {}).get("pagination", {})
            page = pagination.get("page", 1)

            logger.info(f"Getting ledger for member {member_id}, account {active_account_id}, page {page}")

            # Make API call
            url = f"getLedger/{member_id}/{active_account_id}"
            headers = {
                "Content-Type": "application/json",
                "x-client-api-key": config("CLIENT_API_KEY"),
            }
            params = {"page": page} if page > 1 else {}

            response = make_api_request(url, headers, params)

            # Let handlers update state
            response_data, error = handle_api_response(
                response=response,
                state_manager=self.state_manager
            )
            if error:
                logger.error(f"Failed to get ledger: {error}")
                return ValidationResult.failure(
                    message=f"Failed to get ledger: {error}",
                    field="api_call",
                    details={"error": error}
                )

            # Store ledger data for display
            entries = response_data.get("data", {}).get("entries", [])
            total_pages = response_data.get("data", {}).get("totalPages", 1)
            current_page = response_data.get("data", {}).get("currentPage", 1)

            self.update_component_data(data={
                "entries": entries,
                "pagination": {
                    "total_pages": total_pages,
                    "current_page": current_page
                }
            })

            # Set component result for flow control
            action = self.state_manager.get_state_value("action", {})
            if action.get("type") == "LEDGER_RETRIEVED":
                logger.info("Ledger retrieved successfully - proceeding to display")
                self.update_component_data(component_result="show_ledger")
            else:
                logger.info("Unexpected action type after getting ledger")
                self.update_component_data(component_result="show_error")

            return ValidationResult.success({
                "action": action,
                "entries": entries,
                "total_pages": total_pages,
                "current_page": current_page
            })

        except Exception as e:
            logger.error(f"Error in get ledger API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to get ledger: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Most data is in dashboard state, we just need
        ledger data and action details here.
        """
        return {
            "entries": value.get("entries", []),
            "total_pages": value.get("total_pages", 1),
            "current_page": value.get("current_page", 1),
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
