"""Upgrade member tier API call component

Handles upgrading a member's tier through the API:
- Validates required data from state
- Makes API call to upgrade tier
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


class UpgradeMembertierApiCall(ApiComponent):
    """Handles upgrading member tier and managing state"""

    def __init__(self):
        super().__init__("upgrade_membertier_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing member data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process member tier upgrade and update state"""
        try:
            # Get dashboard data from state
            dashboard = self.state_manager.get_state_value("dashboard")
            if not dashboard:
                return ValidationResult.failure(
                    message="No dashboard data found",
                    field="dashboard",
                    details={"component": self.type}
                )

            # Get member data
            member = dashboard.get("member", {})
            member_id = member.get("memberID")
            current_tier = member.get("memberTier")

            if not member_id:
                return ValidationResult.failure(
                    message="No member ID found in dashboard",
                    field="member_id",
                    details={"component": self.type}
                )

            logger.info(f"Upgrading member {member_id} from tier {current_tier}")

            # Make API call
            url = f"upgradeMemberTier/{member_id}"
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
                logger.error(f"Failed to upgrade member tier: {error}")
                return ValidationResult.failure(
                    message=f"Upgrade failed: {error}",
                    field="api_call",
                    details={"error": error}
                )

            # Clear any upgrade-related data
            self.update_component_data(data={})

            # Set component result for flow control
            action = self.state_manager.get_state_value("action", {})
            if action.get("type") == "MEMBER_UPGRADED":
                logger.info("Member upgraded successfully - proceeding to dashboard")
                self.update_component_data(component_result="show_dashboard")
            else:
                logger.info("Unexpected action type after upgrading member")
                self.update_component_data(component_result="show_error")

            return ValidationResult.success({
                "action": action,
                "upgraded": True,
                "previous_tier": current_tier,
                "new_tier": response_data.get("data", {}).get("member", {}).get("memberTier")
            })

        except Exception as e:
            logger.error(f"Error in upgrade member tier API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to upgrade member: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert upgrade response to verified data

        Note: Member data is in dashboard state, we just need
        upgrade status and action details here.
        """
        return {
            "upgrade_complete": True,
            "previous_tier": value.get("previous_tier"),
            "new_tier": value.get("new_tier"),
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
