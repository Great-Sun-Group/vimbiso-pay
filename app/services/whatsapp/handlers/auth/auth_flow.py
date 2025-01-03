"""Authentication flow implementation using component system"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.flow import FlowManager, initialize_flow
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import (ComponentException, FlowException)

logger = logging.getLogger(__name__)


def get_step_content(step: str, data: Optional[Dict] = None) -> str:
    """Get step content without channel formatting"""
    if step == "welcome":
        return (
            "👋 Welcome to VimbisoPay!\n"
            "Let's get you started with registration."
        )
    elif step == "login_error":
        return "❌ Login failed. Please try again."
    return ""


def handle_registration(state_manager: Any) -> Dict:
    """Initialize registration flow using component system"""
    try:
        # Initialize registration flow
        initialize_flow(state_manager, "registration", "welcome")

        # Return welcome content
        return {
            "success": True,
            "content": get_step_content("welcome"),
            "metadata": {"flow": "registration", "step": "welcome"}
        }

    except ComponentException as e:
        # Handle component validation errors
        logger.error("Registration validation error", extra={
            "component": e.component,
            "field": e.field,
            "value": e.value
        })
        error = ErrorHandler.handle_component_error(
            component=e.component,
            field=e.field,
            value=e.value,
            message=str(e)
        )
        return {
            "success": False,
            "content": error["message"],
            "metadata": {"error": error}
        }

    except FlowException as e:
        # Handle flow errors
        logger.error("Registration flow error", extra={
            "step": e.step,
            "action": e.action,
            "data": e.data
        })
        error = ErrorHandler.handle_flow_error(
            step=e.step,
            action=e.action,
            data=e.data,
            message=str(e)
        )
        return {
            "success": False,
            "content": error["message"],
            "metadata": {"error": error}
        }

    except Exception:
        # Handle unexpected errors
        logger.error("Registration error", extra={
            "flow_type": state_manager.get_flow_type(),
            "step": state_manager.get_current_step()
        })
        error = ErrorHandler.handle_system_error(
            code="REGISTRATION_ERROR",
            service="auth_flow",
            action="handle_registration",
            message=ErrorHandler.MESSAGES["system"]["service_error"]
        )
        return {
            "success": False,
            "content": error["message"],
            "metadata": {"error": error}
        }


def attempt_login(state_manager: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Attempt login without state changes

    Args:
        state_manager: State manager instance

    Returns:
        Tuple of (success, response)
        - On success: (True, login_response)
        - On failure: (False, error_response)
    """
    try:
        # Get login component
        flow_manager = FlowManager("auth")
        login_component = flow_manager.get_component("login")

        # Set state manager context
        login_component.state_manager = state_manager

        # Attempt login (triggered by "hi")
        result = login_component.to_verified_data(None)

        # Check login result
        if not result.get("success"):
            # Auth failure - return false with response
            return False, result["response"]

        # Return success response
        return True, result["response"]

    except ComponentException as e:
        # Handle component validation errors
        logger.error("Login validation error", extra={
            "component": e.component,
            "field": e.field,
            "value": e.value
        })
        return False, ErrorHandler.handle_component_error(
            component=e.component,
            field=e.field,
            value=e.value,
            message=str(e)
        )

    except FlowException as e:
        # Handle flow errors
        logger.error("Login flow error", extra={
            "step": e.step,
            "action": e.action,
            "data": e.data
        })
        return False, ErrorHandler.handle_flow_error(
            step=e.step,
            action=e.action,
            data=e.data,
            message=str(e)
        )

    except Exception:
        # Handle unexpected errors
        logger.error("Login error", extra={
            "flow_type": state_manager.get_flow_type(),
            "step": state_manager.get_current_step()
        })
        return False, ErrorHandler.handle_system_error(
            code="LOGIN_ERROR",
            service="auth_flow",
            action="attempt_login",
            message=ErrorHandler.MESSAGES["system"]["service_error"]
        )
