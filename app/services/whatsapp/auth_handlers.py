"""Authentication handlers enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.types import Message
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException

from .handlers.auth.auth_flow import attempt_login, handle_registration
from .handlers.member.display import handle_dashboard_display

logger = logging.getLogger(__name__)


def handle_error(state_manager: Any, operation: str, error: Exception) -> Message:
    """Handle errors consistently

    Args:
        state_manager: State manager instance
        operation: Operation that failed
        error: Exception that occurred

    Returns:
        Message: Registration flow message

    Raises:
        StateException: If error handling fails
    """
    try:
        # Get current flow state
        current_step = state_manager.get_current_step()
        flow_type = state_manager.get_flow_type()

        # Create error context with flow information
        error_context = ErrorContext(
            error_type="flow",
            message=f"{operation} failed: {str(error)}",
            step_id=current_step,
            details={
                "flow_type": flow_type or "auth",
                "operation": operation,
                "error": str(error),
                "auth_failure": True
            }
        )

        # Log error with context
        logger.error(
            f"{operation} failed",
            extra={"error_context": error_context.__dict__}
        )

        # Let ErrorHandler handle state update
        ErrorHandler.handle_error(error, state_manager, error_context)

        # Initialize registration flow state
        state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "welcome"
            }
        })

        return handle_registration(state_manager)

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",
            message="Failed to handle error",
            details={
                "operation": operation,
                "original_error": str(error),
                "handler_error": str(e)
            }
        )
        logger.error(
            "Error handler failed",
            extra={"error_context": error_context.__dict__}
        )
        raise StateException(error_context.message)


def handle_hi(state_manager: Any) -> Message:
    """Handle greeting with login attempt

    Args:
        state_manager: State manager instance

    Returns:
        Message: Dashboard or registration message

    Raises:
        StateException: If greeting handling fails
    """
    try:
        if not state_manager:
            error_context = ErrorContext(
                error_type="state",
                message="State manager is required",
                details={"state_manager": None}
            )
            raise StateException(error_context.message)

        # Let StateManager validate through update_state
        state_manager.update_state({
            "flow_data": {
                "flow_type": "auth",
                "step": 0,
                "current_step": "login"
            }
        })

        # Attempt login (StateManager validates internally)
        success, response = attempt_login(state_manager)

        if success:
            # Update state for dashboard flow
            state_manager.update_state({
                "flow_data": {
                    "flow_type": "dashboard",
                    "step": 0,
                    "current_step": "main"
                }
            })
            logger.info("Login successful, showing dashboard")
            return handle_dashboard_display(state_manager)
        else:
            # Update state for registration flow
            state_manager.update_state({
                "flow_data": {
                    "flow_type": "registration",
                    "step": 0,
                    "current_step": "welcome"
                }
            })
            logger.info(
                "Login failed, starting registration",
                extra={"error": response}
            )
            return handle_registration(state_manager)

    except StateException as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id=state_manager.get_current_step(),
            details={
                "flow_type": "auth",
                "operation": "greeting",
                "error": str(e),
                "auth_failure": True
            }
        )
        return handle_error(state_manager, "Greeting", StateException(error_context.message))
    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to handle greeting",
            step_id=state_manager.get_current_step(),
            details={
                "flow_type": "auth",
                "operation": "greeting",
                "error": str(e),
                "auth_failure": True
            }
        )
        return handle_error(state_manager, "Greeting", StateException(error_context.message))
