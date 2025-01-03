"""Registration handler using component system"""
import logging
from typing import Any, Dict, Optional

from core.messaging.flow import FlowManager, initialize_flow
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException, SystemException
from services.credex.service import register_member

logger = logging.getLogger(__name__)


def get_step_content(step: str, data: Optional[Dict] = None) -> str:
    """Get step content without channel formatting"""
    if step == "welcome":
        return (
            "👋 Welcome to VimbisoPay!\n"
            "Let's get you registered. First, I'll need some information."
        )
    elif step == "firstname":
        return "👤 What is your first name?"
    elif step == "lastname":
        return "👤 What is your last name?"
    elif step == "complete":
        if data:
            return (
                "✅ Registration complete!\n"
                f"Welcome {data.get('firstname')} {data.get('lastname')}!\n"
                "You can now start using VimbisoPay."
            )
        return "✅ Registration complete!"
    return ""


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

        # Return step content
        return {
            "success": True,
            "content": get_step_content(step, state_manager.get_flow_data())
        }

    except ComponentException as e:
        # Handle component validation errors
        logger.error("Registration validation error", extra={
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
        logger.error("Registration flow error", extra={
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
        logger.error("Registration system error", extra={
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
        logger.error("Registration error", extra={
            "step": step,
            "flow_data": state_manager.get_flow_state()
        })
        return ErrorHandler.handle_system_error(
            code="REGISTRATION_ERROR",
            service="registration",
            action="process_step",
            message=ErrorHandler.MESSAGES["system"]["service_error"]
        )


def start_registration(state_manager: Any) -> None:
    """Initialize registration flow"""
    try:
        initialize_flow(state_manager, "registration", "firstname")
    except (ComponentException, FlowException, SystemException):
        # Let caller handle errors
        raise
