"""Upgrade handler using component system"""
import logging
from typing import Any, Dict

from core.messaging.flow import FlowManager, initialize_flow
from core.utils.exceptions import ComponentException, FlowException, SystemException
from services.credex.service import upgrade_member_tier

logger = logging.getLogger(__name__)


def process_upgrade_step(state_manager: Any, step: str, input_value: Any) -> Dict:
    """Process upgrade step using component system

    Args:
        state_manager: State manager instance
        step: Current step
        input_value: Input value for step

    Returns:
        Step result or error
    """
    try:
        # Get flow manager and component
        flow_manager = FlowManager("upgrade")
        component = flow_manager.get_component(step)

        # Process step
        if step == "confirm":
            # Get required data
            member_id = state_manager.get("member_id")
            active_account_id = state_manager.get("active_account_id")

            # Create confirmation data
            confirm_data = {
                "confirmed": input_value.get("confirmed", False),
                "member_id": member_id,
                "account_id": active_account_id
            }

            # Validate confirmation
            result = component.validate(confirm_data)
            if "error" in result:
                return result

            # Convert to verified data
            verified_data = component.to_verified_data(confirm_data)
            state_manager.update_state({
                "flow_data": {
                    "data": verified_data
                }
            })

        elif step == "complete":
            # Get verified data
            flow_data = state_manager.get_flow_data()
            member_id = flow_data["member_id"]
            account_id = flow_data["account_id"]

            # Attempt upgrade
            success, response = upgrade_member_tier(member_id, account_id)
            if not success:
                raise SystemException(
                    message="Failed to upgrade member tier",
                    code="UPGRADE_ERROR",
                    service="upgrade",
                    action="upgrade_tier"
                )

            # Validate upgrade response
            component.validate(response)
            verified_data = component.to_verified_data(response)

            # Update state with verified data
            state_manager.update_state({
                "flow_data": {
                    "data": verified_data
                },
                "member_data": {
                    **state_manager.get("member_data", {}),
                    "memberTier": verified_data["new_tier"]
                }
            })

        return {"success": True}

    except ComponentException as e:
        # Component validation error
        logger.error(f"Upgrade validation error: {str(e)}")
        return {
            "error": {
                "type": "validation",
                "message": str(e),
                "details": e.details
            }
        }
    except FlowException as e:
        # Flow error
        logger.error(f"Upgrade flow error: {str(e)}")
        return {
            "error": {
                "type": "flow",
                "message": str(e),
                "details": e.details
            }
        }
    except SystemException as e:
        # System error
        logger.error(f"Upgrade system error: {str(e)}")
        return {
            "error": {
                "type": "system",
                "message": str(e),
                "details": e.details
            }
        }
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected upgrade error: {str(e)}")
        return {
            "error": {
                "type": "system",
                "message": "Unexpected upgrade error",
                "details": {"error": str(e)}
            }
        }


def start_upgrade(state_manager: Any) -> None:
    """Initialize upgrade flow"""
    initialize_flow(state_manager, "upgrade", "confirm")
