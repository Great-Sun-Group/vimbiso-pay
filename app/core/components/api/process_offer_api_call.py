"""Process offer API call component

Handles credex offer processing through the API:
- Gets required data from state (member, account, offer)
- Makes API call to process offer (accept/decline/cancel)
- Updates state with response
- Sets component_result for flow control
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.api.base import handle_api_response, make_api_request
from core.error.types import ValidationResult

from ..base import ApiComponent

logger = logging.getLogger(__name__)

# API endpoints and action types for each context
API_CONFIG = {
    "process_offer": {  # Default action
        "url": "acceptCredex",
        "success_action": "CREDEX_ACCEPTED",
        "error_prefix": "process",
        "emoji": "✅"
    },
    "accept_offer": {
        "url": "acceptCredex",
        "success_action": "CREDEX_ACCEPTED",
        "error_prefix": "accept",
        "emoji": "✅"
    },
    "decline_offer": {
        "url": "declineCredex",
        "success_action": "CREDEX_DECLINED",
        "error_prefix": "decline",
        "emoji": "❌"
    },
    "cancel_offer": {
        "url": "cancelCredex",
        "success_action": "CREDEX_CANCELLED",
        "error_prefix": "cancel",
        "emoji": "🚫"
    }
}


class ProcessOfferApiCall(ApiComponent):
    """Processes credex offer actions and manages state"""

    def __init__(self):
        super().__init__("process_offer_api")

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process offer action and update state"""
        try:
            # Get required data from state
            member_id, account_id, credex_id = self._get_required_data()
            if not all([member_id, account_id, credex_id]):
                return ValidationResult.failure(
                    message="Missing required data for offer action",
                    field="state",
                    details={
                        "member_id": bool(member_id),
                        "account_id": bool(account_id),
                        "credex_id": bool(credex_id)
                    }
                )

            # Get context and config
            context = self.state_manager.get_path()
            config = API_CONFIG.get(context, API_CONFIG["process_offer"])

            logger.info(
                f"{context.replace('_', ' ').title()} offer {credex_id} for member {member_id} "
                f"on account {account_id}"
            )

            # Make API call
            result = self._make_api_call(member_id, account_id, credex_id, config)
            if not result.valid:
                return result

            # Process response and update state
            return self._process_response(result.value, config)

        except Exception as e:
            logger.error(f"Error in offer API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to process offer: {str(e)}",
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
        credex_id: str,
        config: Dict[str, str]
    ) -> ValidationResult:
        """Make API call to process offer"""
        try:
            # Make request
            response = make_api_request(
                url=config["url"],
                payload={"credexID": credex_id},
                method="POST",
                state_manager=self.state_manager
            )

            # Process response
            result, error = handle_api_response(
                response=response,
                state_manager=self.state_manager
            )
            if error:
                logger.error(f"Failed to {config['error_prefix']} offer: {error}")
                return ValidationResult.failure(
                    message=f"Failed to {config['error_prefix']} offer: {error}",
                    field="api_call",
                    details={"error": error}
                )

            return ValidationResult.success(result)

        except Exception as e:
            logger.error(f"Error making API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to {config['error_prefix']} offer: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _process_response(self, response: Dict, config: Dict[str, str]) -> ValidationResult:
        """Process API response and update state"""
        try:
            # Clear offer data
            self.update_component_data(data={})

            # Set component result based on action
            action = self.state_manager.get_state_value("action", {})
            action_type = action.get("type")

            if action_type == config["success_action"]:
                logger.info(f"Offer {config['error_prefix']}ed successfully")

                # Send success notification
                self.state_manager.messaging.send_text(f"{config['emoji']} Credex offer {config['error_prefix']}ed")

                # Check for more pending offers
                dashboard = self.state_manager.get_state_value("dashboard", {})
                active_account_id = self.state_manager.get_state_value("active_account_id")
                active_account = next(
                    (acc for acc in dashboard.get("accounts", []) if acc.get("accountID") == active_account_id),
                    None
                )

                # Get context to check correct offer list
                context = self.state_manager.get_path()
                offer_list = (
                    active_account.get("pendingInData", [])
                    if context in {"process_offer", "accept_offer", "decline_offer"}
                    else active_account.get("pendingOutData", [])
                )

                # Return to list if more offers, otherwise to dashboard
                if active_account and offer_list:
                    self.update_component_data(component_result="return_to_list")
                else:
                    self.update_component_data(component_result="send_dashboard")
            else:
                logger.warning(f"Unexpected action type: {action_type}")
                self.update_component_data(component_result="show_error")

            return ValidationResult.success({
                "action": action,
                "success": action_type == config["success_action"]
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
        We just track action status here.
        """
        return {
            "success": value.get("success", False),
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
