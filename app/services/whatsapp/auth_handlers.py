"""Authentication handlers enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.types import Message
from core.utils.exceptions import ComponentException, FlowException, SystemException

from .handlers.auth.auth_flow import attempt_login, handle_registration
from .handlers.member.display import handle_dashboard_display
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


def handle_error(state_manager: Any, operation: str, error: Exception) -> Message:
    """Handle errors consistently

    Args:
        state_manager: State manager instance
        operation: Operation that failed
        error: Exception that occurred

    Returns:
        Message: Registration flow message
    """
    try:
        # Get channel ID for error response
        channel_id = state_manager.get_channel_id()

        # Log error with context
        logger.error(
            f"{operation} failed",
            extra={
                "operation": operation,
                "error": str(error),
                "flow_type": state_manager.get_flow_type(),
                "step": state_manager.get_current_step()
            }
        )

        # Initialize registration flow state
        state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "welcome",
                "type": "registration_start",
                "data": {
                    "error": str(error)
                }
            }
        })

        return handle_registration(state_manager)

    except Exception as e:
        # Handle unexpected errors
        error = SystemException(
            message=f"Failed to handle error: {str(e)}",
            code="ERROR_HANDLER_ERROR",
            service="auth_handlers",
            action="handle_error",
            details={
                "operation": operation,
                "original_error": str(error)
            }
        )
        logger.error(
            "Error handler failed",
            extra={"error": str(error)}
        )
        return WhatsAppMessage.create_text(
            channel_id if 'channel_id' in locals() else "unknown",
            f"❌ {str(error)}"
        )


def handle_hi(state_manager: Any) -> Message:
    """Handle greeting with login attempt

    Args:
        state_manager: State manager instance

    Returns:
        Message: Dashboard or registration message
    """
    try:
        # Validate state manager
        if not state_manager:
            raise ComponentException(
                message="State manager is required",
                component="auth_handlers",
                field="state_manager",
                value="None"
            )

        # Attempt login (handles state management internally)
        success, response = attempt_login(state_manager)

        if success:
            # Extract data from response
            data = response.get("data", {})
            action = data.get("action", {})
            dashboard = data.get("dashboard", {})

            # Extract auth details
            auth_details = action.get("details", {})
            member_data = dashboard.get("member", {})
            accounts = dashboard.get("accounts", [])

            # First update auth state
            success, error = state_manager.update_state({
                "member_id": auth_details.get("memberID"),
                "jwt_token": auth_details.get("token"),
                "authenticated": True,
                "member_data": member_data,
                "accounts": accounts,
                "active_account_id": accounts[0]["accountID"] if accounts else None
            })
            if not success:
                raise FlowException(
                    message=f"Failed to update auth state: {error}",
                    step="login",
                    action="update_auth",
                    data={"error": error}
                )

            # Then update flow state
            success, error = state_manager.update_state({
                "flow_data": {
                    "flow_type": "dashboard",
                    "step": 0,
                    "current_step": "main",
                    "type": "dashboard_display",
                    "data": {
                        "member_id": auth_details.get("memberID")
                    }
                }
            })
            if not success:
                raise FlowException(
                    message=f"Failed to update flow state: {error}",
                    step="login",
                    action="update_flow",
                    data={"error": error}
                )

            logger.info("Login successful, showing dashboard")
            return handle_dashboard_display(state_manager)
        else:
            # Update state for registration flow
            state_manager.update_state({
                "flow_data": {
                    "flow_type": "registration",
                    "step": 0,
                    "current_step": "welcome",
                    "type": "registration_start",
                    "data": {
                        "error": response
                    }
                }
            })
            logger.info(
                "Login failed, starting registration",
                extra={"error": response}
            )
            return handle_registration(state_manager)

    except (ComponentException, FlowException) as e:
        # Handle validation and flow errors
        return handle_error(state_manager, "Greeting", e)

    except Exception as e:
        # Handle unexpected errors
        error = SystemException(
            message=str(e),
            code="AUTH_ERROR",
            service="auth_handlers",
            action="handle_greeting"
        )
        return handle_error(state_manager, "Greeting", error)
