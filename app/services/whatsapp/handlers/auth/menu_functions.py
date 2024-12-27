"""Menu handling functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

from ..member.dashboard import handle_dashboard_display

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def create_error_message(state_manager: Any, error_msg: str, error_type: str = "ERROR_INTERNAL", error_code: str = "REQUEST_ERROR") -> Message:
    """Create error message using core message types"""
    try:
        # Validate channel info before access
        channel = state_manager.get("channel")
        if not channel or "identifier" not in channel:
            raise StateException("Invalid channel information")

        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="❌ Error: Unable to process request. Please try again."
            ),
            metadata={
                "error": {
                    "type": error_type,
                    "code": error_code,
                    "message": error_msg
                }
            }
        )

    except StateException as e:
        logger.error(f"Failed to create error message: {str(e)}")
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body="❌ Critical Error: System temporarily unavailable"
            ),
            metadata={
                "error": {
                    "type": "ERROR_CRITICAL",
                    "code": "SYSTEM_ERROR",
                    "message": str(e)
                }
            }
        )


def show_dashboard(state_manager: Any) -> Message:
    """Display dashboard"""
    try:
        return handle_dashboard_display(state_manager)

    except StateException as e:
        logger.error(f"Dashboard display error: {str(e)}")
        return create_error_message(
            state_manager=state_manager,
            error_msg=str(e),
            error_type="ERROR_VALIDATION",
            error_code="DASHBOARD_ERROR"
        )


def handle_menu(state_manager: Any) -> Message:
    """Display main menu"""
    try:
        if state_manager.get("authenticated"):
            return show_dashboard(state_manager)

        from .auth_flow import handle_registration

        # Check if login is required
        if state_manager.get("login_required"):
            success, error = state_manager.update_state({
                "flow_action": "login",
                "login_required": False,  # Reset after use
                "flow_data": {
                    "flow_type": "auth",
                    "step": 0,
                    "current_step": "login"
                }
            })
        else:
            success, error = state_manager.update_state({
                "flow_action": "register",
                "flow_data": {
                    "flow_type": "auth",
                    "step": 0,
                    "current_step": "registration"
                }
            })

        if not success:
            raise StateException(f"Failed to update state: {error}")
        return handle_registration(state_manager)

    except StateException as e:
        logger.error(f"Menu display error: {str(e)}")
        return create_error_message(
            state_manager=state_manager,
            error_msg=str(e),
            error_type="ERROR_VALIDATION",
            error_code="MENU_ERROR"
        )


def handle_hi(state_manager: Any) -> Message:
    """Handle initial greeting enforcing SINGLE SOURCE OF TRUTH"""
    try:
        from .auth_flow import attempt_login
        success, response = attempt_login(state_manager)

        if success:
            # State is already updated by attempt_login
            # Verify authentication state
            if not state_manager.get("authenticated"):
                raise StateException("Authentication state not properly set")

            # Return menu for authenticated user
            return handle_menu(state_manager)

        # Handle login failure
        if response is None:
            # User not found - start registration
            success, error = state_manager.update_state({
                "flow_action": "register",
                "authenticated": False,
                "flow_data": {
                    "flow_type": "auth",
                    "step": 0,
                    "current_step": "registration"
                }
            })
            if not success:
                raise StateException(f"Failed to update state: {error}")
            from .auth_flow import handle_registration
            return handle_registration(state_manager)

        # Return error message for other failures
        return create_error_message(
            state_manager=state_manager,
            error_msg="Login failed. Please try again.",
            error_type="ERROR_AUTH",
            error_code="LOGIN_FAILED"
        )

    except StateException as e:
        logger.error(f"Greeting error: {str(e)}")
        return create_error_message(
            state_manager=state_manager,
            error_msg=str(e),
            error_type="ERROR_VALIDATION",
            error_code="GREETING_ERROR"
        )


def handle_refresh(state_manager: Any) -> Message:
    """Handle dashboard refresh"""
    try:
        success, error = state_manager.update_state({
            "dashboard_message": "Dashboard refreshed",
            "flow_data": {
                "flow_type": "dashboard",
                "step": 0,
                "current_step": "refresh"
            }
        })
        if not success:
            raise StateException(f"Failed to update state: {error}")
        return handle_menu(state_manager)

    except StateException as e:
        logger.error(f"Refresh error: {str(e)}")
        return create_error_message(
            state_manager=state_manager,
            error_msg=str(e),
            error_type="ERROR_VALIDATION",
            error_code="REFRESH_ERROR"
        )
