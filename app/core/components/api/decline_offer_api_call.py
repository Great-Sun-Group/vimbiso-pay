"""Decline offer API call component

Handles declining a Credex offer through the API:
- Gets required data from state (member, account, offer)
- Makes API call to decline offer
- Updates state with response
- Sets component_result for flow control
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.error.types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent

logger = logging.getLogger(__name__)


class DeclineOfferApiCall(ApiComponent):
    """Processes offer decline and manages state"""

    def __init__(self):
        super().__init__("decline_offer_api")

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process offer decline and update state"""
        try:
            # Get required data from state
            member_id, account_id, credex_id = self._get_required_data()
            if not all([member_id, account_id, credex_id]):
                return ValidationResult.failure(
                    message="Missing required data for declining offer",
                    field="state",
                    details={
                        "member_id": bool(member_id),
                        "account_id": bool(account_id),
                        "credex_id": bool(credex_id)
                    }
                )

            logger.info(
                f"Declining offer {credex_id} for member {member_id} "
                f"on account {account_id}"
            )

            # Make API call
            result = self._make_api_call(member_id, account_id, credex_id)
            if not result.valid:
                return result

            # Process response and update state
            return self._process_response(result.value)

        except Exception as e:
            logger.error(f"Error in decline offer API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to decline offer: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _get_required_data(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get required data from state"""
        try:
            # Get member ID from dashboard
            dashboard = self.state_manager.get_state_value("dashboard", {})
            member_id = dashboard.get("member", {}).get("memberID")

            # Get active account ID
            account_id = self.state_manager.get_state_value("active_account_id")

            # Get credex ID from component data
            component_data = self.state_manager.get_state_value("component_data", {})
            credex_id = component_data.get("data", {}).get("credex_id")

            return member_id, account_id, credex_id

        except Exception as e:
            logger.error(f"Error getting required data: {str(e)}")
            return None, None, None

    def _make_api_call(
        self,
        member_id: str,
        account_id: str,
        credex_id: str
    ) -> ValidationResult:
        """Make API call to decline offer"""
        try:
            # Make request
            url = f"declineOffer/{member_id}/{account_id}/{credex_id}"
            response = make_api_request(
                url=url,
                payload={},
                method="POST",
                state_manager=self.state_manager
            )

            # Process response
            result, error = handle_api_response(
                response=response,
                state_manager=self.state_manager
            )
            if error:
                logger.error(f"Failed to decline offer: {error}")
                return ValidationResult.failure(
                    message=f"Failed to decline offer: {error}",
                    field="api_call",
                    details={"error": error}
                )

            return ValidationResult.success(result)

        except Exception as e:
            logger.error(f"Error making API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to decline offer: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _process_response(self, response: Dict) -> ValidationResult:
        """Process API response and update state"""
        try:
            # Clear offer data
            self.update_component_data(data={})

            # Set component result based on action
            action = self.state_manager.get_state_value("action", {})
            action_type = action.get("type")

            if action_type == "OFFER_DECLINED":
                logger.info("Offer declined successfully")
                self.update_component_data(component_result="send_dashboard")
            else:
                logger.warning(f"Unexpected action type: {action_type}")
                self.update_component_data(component_result="show_error")

            return ValidationResult.success({
                "action": action,
                "offer_declined": action_type == "OFFER_DECLINED"
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
        We just track decline status here.
        """
        return {
            "offer_declined": value.get("offer_declined", False),
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
