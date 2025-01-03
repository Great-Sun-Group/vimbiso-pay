"""Authentication handlers enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.flow import initialize_flow
from core.messaging.types import (ChannelIdentifier, Message, MessageRecipient,
                                  TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException

from .handlers.auth.auth_flow import attempt_login
from .handlers.member.display import handle_dashboard_display
from .handlers.message.message_handler import process_message

logger = logging.getLogger(__name__)


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

        # Attempt login (handles system errors internally)
        success, response = attempt_login(state_manager)

        if success:
            # Login successful - extract data from response
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
            # Login failed - start registration
            logger.info("User not found, starting registration")
            # Initialize registration flow (first step from registry)
            initialize_flow(state_manager, "registration")
            # Process through message handler for consistent message creation
            return process_message(state_manager, "text", "hi")

    except ComponentException as e:
        # Handle component validation errors
        logger.error("Auth validation error", extra={
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
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=state_manager.get("channel")["type"],
                    value=state_manager.get_channel_id()
                )
            ),
            content=TextContent(error["message"]),
            metadata={"error": error}
        )

    except FlowException as e:
        # Handle flow errors
        logger.error("Auth flow error", extra={
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
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=state_manager.get("channel")["type"],
                    value=state_manager.get_channel_id()
                )
            ),
            content=TextContent(error["message"]),
            metadata={"error": error}
        )

    except Exception:
        # Handle unexpected errors
        logger.error("Auth error", extra={
            "flow_type": state_manager.get_flow_type(),
            "step": state_manager.get_current_step()
        })
        error = ErrorHandler.handle_system_error(
            code="AUTH_ERROR",
            service="auth_handlers",
            action="handle_greeting",
            message=ErrorHandler.MESSAGES["system"]["service_error"]
        )
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=state_manager.get("channel")["type"],
                    value=state_manager.get_channel_id()
                )
            ),
            content=TextContent(error["message"]),
            metadata={"error": error}
        )
