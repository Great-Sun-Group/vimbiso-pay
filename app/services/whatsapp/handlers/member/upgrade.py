"""Upgrade handler using component system"""
import logging
from typing import Any, Dict, Optional

from core.messaging.flow import FlowManager, initialize_flow
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException, SystemException
from services.credex.service import upgrade_member_tier

logger = logging.getLogger(__name__)


def get_step_content(step: str, data: Optional[Dict] = None) -> str:
    """Get step content without channel formatting"""
    if step == "confirm":
        return (
            "⭐ Upgrade Member Tier\n"
            "This will upgrade your account to the next tier level.\n"
            "Please confirm (yes/no):"
        )
    elif step == "complete":
        if data and data.get("new_tier"):
            return f"✅ Successfully upgraded to Tier {data['new_tier']}!"
        return "✅ Upgrade completed successfully!"
    return ""


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

        # Return step content
        return {
            "success": True,
            "content": get_step_content(step, state_manager.get_flow_data()),
            "actions": ["confirm", "cancel"] if step == "confirm" else None
        }

    except ComponentException as e:
        # Handle component validation errors
        logger.error("Upgrade validation error", extra={
            "component": e.component,
            "field": e.field,
            "value": e.value
        })
        return ErrorHandler.handle_component_error(
            component=e.component,
            field=e.field,
            value=e.value,
            message=str(e)
        )

    except FlowException as e:
        # Handle flow errors
        logger.error("Upgrade flow error", extra={
            "step": e.step,
            "action": e.action,
            "data": e.data
        })
        return ErrorHandler.handle_flow_error(
            step=e.step,
            action=e.action,
            data=e.data,
            message=str(e)
        )

    except SystemException as e:
        # Handle system errors
        logger.error("Upgrade system error", extra={
            "code": e.code,
            "service": e.service,
            "action": e.action
        })
        return ErrorHandler.handle_system_error(
            code=e.code,
            service=e.service,
            action=e.action,
            message=str(e)
        )

    except Exception:
        # Handle unexpected errors
        logger.error("Unexpected upgrade error", extra={
            "step": step,
            "flow_data": state_manager.get_flow_state()
        })
        return ErrorHandler.handle_system_error(
            code="UPGRADE_ERROR",
            service="upgrade",
            action="process_step",
            message=ErrorHandler.MESSAGES["system"]["service_error"]
        )


def start_upgrade(state_manager: Any) -> None:
    """Initialize upgrade flow"""
    initialize_flow(state_manager, "upgrade", "confirm")
