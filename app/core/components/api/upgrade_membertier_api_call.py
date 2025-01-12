"""Upgrade member tier API call component

Handles upgrading a member's tier through the API:
- Gets required data from state (member, account)
- Makes API call to upgrade tier
- Updates state with response
- Sets component_result for flow control
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.error.types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent

logger = logging.getLogger(__name__)


class UpgradeMembertierApiCall(ApiComponent):
    """Processes member tier upgrade and manages state"""

    def __init__(self):
        super().__init__("upgrade_membertier_api")

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process member tier upgrade and update state"""
        try:
            # Get required data from state
            member_id, current_tier = self._get_required_data()
            if not all([member_id, current_tier is not None]):
                return ValidationResult.failure(
                    message="Missing required data for upgrading member tier",
                    field="state",
                    details={
                        "member_id": bool(member_id),
                        "current_tier": current_tier is not None
                    }
                )

            logger.info(
                f"Upgrading member {member_id} from tier {current_tier} "
                f"to tier {current_tier + 1}"
            )

            # Make API call
            result = self._make_api_call(member_id)
            if not result.valid:
                return result

            # Process response and update state
            return self._process_response(result.value, current_tier)

        except Exception as e:
            logger.error(f"Error in upgrade member tier API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to upgrade member: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _get_required_data(self) -> Tuple[Optional[str], Optional[int]]:
        """Get required data from state"""
        try:
            # Get member data from dashboard
            dashboard = self.state_manager.get_state_value("dashboard", {})
            member = dashboard.get("member", {})
            member_id = member.get("memberID")
            current_tier = member.get("memberTier")

            return member_id, current_tier

        except Exception as e:
            logger.error(f"Error getting required data: {str(e)}")
            return None, None

    def _make_api_call(self, member_id: str) -> ValidationResult:
        """Make API call to upgrade member tier"""
        try:
            # Make request
            url = f"upgradeMemberTier/{member_id}"
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
                logger.error(f"Failed to upgrade member tier: {error}")
                return ValidationResult.failure(
                    message=f"Failed to upgrade member tier: {error}",
                    field="api_call",
                    details={"error": error}
                )

            return ValidationResult.success(result)

        except Exception as e:
            logger.error(f"Error making API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to upgrade member tier: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _process_response(self, response: Dict, previous_tier: int) -> ValidationResult:
        """Process API response and update state"""
        try:
            # Clear upgrade data
            self.update_component_data(data={})

            # Set component result based on action
            action = self.state_manager.get_state_value("action", {})
            action_type = action.get("type")

            if action_type == "MEMBER_UPGRADED":
                logger.info("Member upgraded successfully")
                self.update_component_data(component_result="send_dashboard")
            else:
                logger.warning(f"Unexpected action type: {action_type}")
                self.update_component_data(component_result="show_error")

            # Get new tier from response
            new_tier = response.get("data", {}).get("member", {}).get("memberTier")

            return ValidationResult.success({
                "action": action,
                "upgraded": action_type == "MEMBER_UPGRADED",
                "previous_tier": previous_tier,
                "new_tier": new_tier
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
        We just track upgrade status here.
        """
        return {
            "upgrade_complete": value.get("upgraded", False),
            "previous_tier": value.get("previous_tier"),
            "new_tier": value.get("new_tier"),
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
