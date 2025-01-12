"""Get ledger API call component

Handles retrieving paginated ledger entries through the API:
- Gets pagination params from component_data
- Makes API call to get ledger entries
- Updates state with response
- Passes data back to input component
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.error.types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent

logger = logging.getLogger(__name__)


class GetLedgerApiCall(ApiComponent):
    """Processes ledger retrieval and manages state"""

    def __init__(self):
        super().__init__("get_ledger_api")

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process ledger retrieval and update state"""
        try:
            # Get required data from state
            account_id, start_row, num_rows = self._get_required_data()
            if not account_id:
                return ValidationResult.failure(
                    message="Missing required data for retrieving ledger",
                    field="state",
                    details={
                        "account_id": bool(account_id)
                    }
                )

            logger.info(
                f"Retrieving ledger for account {account_id} "
                f"(start: {start_row}, rows: {num_rows})"
            )

            # Make API call
            result = self._make_api_call(account_id, start_row, num_rows)
            if not result.valid:
                return result

            # Process response and update state
            return self._process_response(result.value)

        except Exception as e:
            logger.error(f"Error in get ledger API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to retrieve ledger: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _get_required_data(self) -> Tuple[Optional[str], Optional[int], Optional[int]]:
        """Get required data from state"""
        try:
            # Get pagination data from component_data
            component_data = self.state_manager.get_state_value("component_data", {})
            data = component_data.get("data", {})
            account_id = data.get("account_id")
            start_row = data.get("start_row", 0)
            num_rows = data.get("num_rows", 7)  # Default to 7 rows

            return account_id, start_row, num_rows

        except Exception as e:
            logger.error(f"Error getting required data: {str(e)}")
            return None, None, None

    def _make_api_call(
        self,
        account_id: str,
        start_row: int,
        num_rows: int
    ) -> ValidationResult:
        """Make API call to get ledger entries"""
        try:
            # Make request
            url = "getLedger"
            payload = {
                "accountID": account_id,
                "startRow": start_row,
                "numRows": num_rows
            }

            response = make_api_request(
                url=url,
                payload=payload,
                method="POST",
                state_manager=self.state_manager
            )

            # Process response
            result, error = handle_api_response(
                response=response,
                state_manager=self.state_manager
            )
            if error:
                logger.error(f"Failed to retrieve ledger: {error}")
                return ValidationResult.failure(
                    message=f"Failed to retrieve ledger: {error}",
                    field="api_call",
                    details={"error": error}
                )

            return ValidationResult.success(result)

        except Exception as e:
            logger.error(f"Error making API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to retrieve ledger: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _process_response(self, response: Dict) -> ValidationResult:
        """Process API response and update state"""
        try:
            # Get account details for display
            dashboard = self.state_manager.get_state_value("dashboard", {})
            active_account_id = self.state_manager.get_state_value("active_account_id")
            account = next(
                (acc for acc in dashboard.get("accounts", [])
                 if acc.get("accountID") == active_account_id),
                None
            )
            if not account:
                return ValidationResult.failure(
                    message="Active account not found",
                    field="account",
                    details={"active_account_id": active_account_id}
                )

            # Get ledger data from response
            action = response.get("data", {}).get("action", {})
            ledger_data = action.get("details", {}).get("ledger", [])
            pagination = response.get("data", {}).get("dashboard", {}).get("pagination", {})

            # Pass data to input component for display
            from ..input.view_ledger import ViewLedger
            view_ledger = ViewLedger()
            view_ledger.set_state_manager(self.state_manager)
            view_ledger.display_entries(
                entries=ledger_data,
                has_more=pagination.get("hasMore", False),
                account_name=account.get("accountName", "Unknown"),
                account_handle=account.get("accountHandle", "Unknown")
            )

            # Set component result based on action
            action_type = action.get("type")
            if action_type == "LEDGER_RETRIEVED":
                logger.info("Ledger retrieved successfully")
                self.update_component_data(component_result="display_entries")
            else:
                logger.warning(f"Unexpected action type: {action_type}")
                self.update_component_data(component_result="show_error")

            return ValidationResult.success({
                "action": action,
                "entries": ledger_data,
                "pagination": pagination
            })

        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to process response: {str(e)}",
                field="response",
                details={"error": str(e)}
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Dashboard/action data is handled by handle_api_response.
        We just track ledger retrieval status here.
        """
        return {
            "ledger_retrieved": True,
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id"),
            "has_more": value.get("pagination", {}).get("hasMore", False)
        }
