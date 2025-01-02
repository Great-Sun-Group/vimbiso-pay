"""Registration handler using component system"""
import logging
from typing import Any, Dict

from core.messaging.flow import FlowManager, initialize_flow
from core.utils.exceptions import ComponentException, FlowException, SystemException
from services.credex.service import register_member

logger = logging.getLogger(__name__)


def process_registration_step(state_manager: Any, step: str, input_value: Any) -> Dict:
    """Process registration step using component system

    Args:
        state_manager: State manager instance
        step: Current step
        input_value: Input value for step

    Returns:
        Step result or error
    """
    try:
        # Get flow manager and component
        flow_manager = FlowManager("registration")
        component = flow_manager.get_component(step)

        # Process step
        if step == "firstname":
            # Validate and store first name
            result = component.validate(input_value)
            if "error" in result:
                return result

            verified_data = component.to_verified_data(input_value)
            state_manager.update_state({
                "flow_data": {
                    "data": verified_data
                }
            })

        elif step == "lastname":
            # Validate and store last name
            result = component.validate(input_value)
            if "error" in result:
                return result

            verified_data = component.to_verified_data(input_value)
            state_manager.update_state({
                "flow_data": {
                    "data": verified_data
                }
            })

        elif step == "complete":
            # Get stored registration data
            flow_data = state_manager.get_flow_data()
            registration_data = {
                "firstname": flow_data.get("firstname"),
                "lastname": flow_data.get("lastname"),
                "defaultDenom": "USD"  # Always USD for now
            }

            # Get channel ID
            phone = state_manager.get_channel_id()

            # Register member
            success, response = register_member(phone, registration_data)
            if not success:
                raise SystemException(
                    message="Failed to register member",
                    code="REGISTRATION_ERROR",
                    service="registration",
                    action="register"
                )

            # Validate registration response
            component.validate(response)
            verified_data = component.to_verified_data(response)

            # Update state with verified data
            state_manager.update_state({
                # Core identity - SINGLE SOURCE OF TRUTH
                "jwt_token": verified_data["jwt_token"],
                "authenticated": True,
                "member_id": verified_data["member_id"],

                # Member data at top level
                "member_data": {
                    "memberTier": 1,  # Always 1 for new members
                    "firstname": registration_data["firstname"],
                    "lastname": registration_data["lastname"],
                    "defaultDenom": registration_data["defaultDenom"]
                },

                # Account data at top level
                "accounts": verified_data["accounts"],
                "active_account_id": verified_data["active_account_id"]
            })

        return {"success": True}

    except ComponentException as e:
        # Component validation error
        logger.error(f"Registration validation error: {str(e)}")
        return {
            "error": {
                "type": "validation",
                "message": str(e),
                "details": e.details
            }
        }
    except FlowException as e:
        # Flow error
        logger.error(f"Registration flow error: {str(e)}")
        return {
            "error": {
                "type": "flow",
                "message": str(e),
                "details": e.details
            }
        }
    except SystemException as e:
        # System error
        logger.error(f"Registration system error: {str(e)}")
        return {
            "error": {
                "type": "system",
                "message": str(e),
                "details": e.details
            }
        }
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected registration error: {str(e)}")
        return {
            "error": {
                "type": "system",
                "message": "Unexpected registration error",
                "details": {"error": str(e)}
            }
        }


def start_registration(state_manager: Any) -> None:
    """Initialize registration flow"""
    initialize_flow(state_manager, "registration", "firstname")
