"""Accept offer API call component

Handles accepting a Credex offer through the API:
- Validates required data from state
- Makes API call to accept offer
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


class AcceptOfferApiCall(ApiComponent):
    """Handles accepting a Credex offer and managing state"""

    def __init__(self):
        super().__init__("accept_offer_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process offer acceptance and update state"""
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

            # Get selected offer from component data
            component_data = self.state_manager.get_state_value("component_data", {})
            offer_data = component_data.get("data", {})
            if not offer_data:
                return ValidationResult.failure(
                    message="No offer data found",
                    field="component_data.data",
                    details={"component": self.type}
                )
            credex_id = offer_data.get("credex_id")
            if not credex_id:
                return ValidationResult.failure(
                    message="No Credex ID found",
                    field="credex_id",
                    details={"component": self.type}
                )

            logger.info(f"Accepting offer {credex_id} for member {member_id}")

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
                logger.error(f"Failed to accept offer: {error}")
                return ValidationResult.failure(
                    message=f"Failed to accept offer: {error}",
                    field="api_call",
                    details={"error": error}
                )

            # Clear offer data after successful acceptance
            self.update_component_data(data={})

            # Set component result for flow control
            action = self.state_manager.get_state_value("action", {})
            if action.get("type") == "OFFER_ACCEPTED":
                logger.info("Offer accepted successfully - proceeding to dashboard")
                self.update_component_data(component_result="show_dashboard")
            else:
                logger.info("Unexpected action type after accepting offer")
                self.update_component_data(component_result="show_error")

            return ValidationResult.success({
                "action": action,
                "offer_accepted": True
            })

        except Exception as e:
            logger.error(f"Error in accept offer API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to accept offer: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

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
