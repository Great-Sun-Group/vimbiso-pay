"""Authentication handlers enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.types import Message
from core.utils.error_handler import ErrorContext, ErrorHandler
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
        # Create error context
        error_context = ErrorContext(
            error_type="auth",
            message=f"{operation} failed: {str(error)}",
            details={
                "operation": operation,
                "error": str(error)
            }
        )

        # Log error with context
        logger.error(
            f"{operation} failed",
            extra={"error_context": error_context.__dict__}
        )

        try:
            # Let StateManager validate through state update
            success, update_error = state_manager.update_state({
                "flow_data": {
                    "flow_type": "registration",
                    "step": 0,
                    "current_step": "welcome",
                    "data": {
                        "error": str(error),  # Include error in state for audit
                        "error_type": error_context.error_type,
                        "operation": operation
                    }
                }
            })
            if not success:
                error_context = ErrorContext(
                    error_type="state",
                    message="Failed to update error state",
                    details={
                        "operation": operation,
                        "error": update_error
                    }
                )
                raise StateException(ErrorHandler.handle_error(
                    StateException(update_error),
                    state_manager,
                    error_context
                ))

        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to handle error state",
                details={
                    "operation": operation,
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

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

        # Attempt login (updates state internally)
        success, error = attempt_login(state_manager)
        if not success:
            logger.info(
                "Login failed, starting registration",
                extra={"error": error}
            )
            return handle_registration(state_manager)

        # Login successful - show dashboard (StateManager validates authentication)
        logger.info("Login successful, showing dashboard")
        return handle_dashboard_display(state_manager)

    except StateException as e:
        return handle_error(state_manager, "Greeting", e)
    except Exception as e:
        error_context = ErrorContext(
            error_type="auth",
            message="Failed to handle greeting",
            details={"error": str(e)}
        )
        return handle_error(state_manager, "Greeting", StateException(error_context.message))
