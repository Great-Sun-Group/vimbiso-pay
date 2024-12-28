"""Upgrade handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException
from services.credex.service import upgrade_member_tier

logger = logging.getLogger(__name__)


def handle_upgrade(state_manager: Any, input_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Handle upgrade enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Initialize upgrade flow
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "upgrade",
                "step": 0,
                "current_step": "start",
                "data": {}
            }
        })
        if not success:
            raise StateException(f"Failed to initialize upgrade: {error}")

        # Get member data
        member_id = state_manager.get("member_id")
        if not member_id:
            raise StateException("Member ID required for upgrade")

        # Get current account data
        account_id = state_manager.get("account_id")
        if not account_id:
            raise StateException("Account ID required for upgrade")

        # Update state with upgrade data
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "upgrade",
                "step": 1,
                "current_step": "confirm",
                "data": {
                    "member_id": member_id,
                    "account_id": account_id,
                    "upgrade_data": input_data or {}
                }
            }
        })
        if not success:
            raise StateException(f"Failed to update upgrade state: {error}")

        # If no input data, return to get confirmation
        if not input_data:
            return True, None

        # Validate confirmation
        if not input_data.get("confirmed"):
            raise StateException("Invalid confirmation response")

        # Attempt upgrade
        success, response = upgrade_member_tier(member_id, account_id)
        if not success:
            raise StateException("Failed to upgrade member tier")

        upgrade_data = response["data"]

        # Update state with upgrade complete
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "upgrade",
                "step": 2,
                "current_step": "complete",
                "data": {
                    "upgrade": upgrade_data,
                    "previous_tier": input_data.get("previous_tier"),
                    "new_tier": upgrade_data["tier"]
                }
            }
        })
        if not success:
            raise StateException(f"Failed to update completion state: {error}")

        return True, None

    except StateException as e:
        logger.error(f"Upgrade error: {str(e)}")
        # Update state with error
        state_manager.update_state({
            "flow_data": {
                "flow_type": "upgrade",
                "step": 0,
                "current_step": "error",
                "data": {
                    "error": str(e),
                    "input": input_data
                }
            }
        })
        return False, {
            "error": {
                "type": "UPGRADE_ERROR",
                "message": str(e)
            }
        }
