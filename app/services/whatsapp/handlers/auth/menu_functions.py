"""Menu handling functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Optional, Tuple

from core.messaging.types import (
    ChannelIdentifier, ChannelType, Message, MessageRecipient, TextContent
)
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ..member.dashboard import handle_dashboard_display

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def validate_state(state_manager: Any, required_fields: set) -> Tuple[bool, Optional[str]]:
    """Validate state requirements"""
    try:
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        validation = StateValidator.validate_before_access(
            current_state,
            required_fields
        )

        if not validation.is_valid:
            return False, validation.error_message

        return True, None

    except Exception as e:
        return False, str(e)


def get_channel_info(state_manager: Any) -> Tuple[Optional[dict], Optional[str]]:
    """Get channel info from state"""
    try:
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            return None, "Channel identifier not found"
        return channel, None
    except Exception as e:
        return None, str(e)


def create_error_message(state_manager: Any, error: str) -> Message:
    """Create error message"""
    try:
        # Validate minimum required state
        channel, error = get_channel_info(state_manager)
        if error:
            raise ValueError(error)

        # Get member ID if available
        member_id = state_manager.get("member_id")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id or "pending",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="❌ Error: Unable to process request. Please try again."
            )
        )

    except Exception as e:
        logger.error(f"Failed to create error message: {str(e)}")
        return Message(
            recipient=MessageRecipient(
                member_id="unknown",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body="❌ Critical Error: System temporarily unavailable"
            )
        )


def show_dashboard(state_manager: Any, credex_service: Any, message: Optional[str] = None) -> Message:
    """Display dashboard"""
    try:
        # Validate required state
        valid, error = validate_state(
            state_manager,
            {"channel", "member_id", "account_id", "authenticated", "jwt_token"}
        )
        if not valid:
            raise ValueError(error)

        # Get channel info
        channel, error = get_channel_info(state_manager)
        if error:
            raise ValueError(error)

        logger.info(f"Displaying dashboard for channel {channel['identifier']}")
        return handle_dashboard_display(
            state_manager=state_manager,
            credex_service=credex_service,
            success_message=message,
            flow_type="dashboard"
        )

    except ValueError as e:
        logger.error(f"Dashboard display error: {str(e)}")

    except ValueError as e:
        logger.error(f"Dashboard display error: {str(e)}")
        return create_error_message(state_manager, str(e))


def handle_menu(state_manager: Any, auth_flow: Any, message: Optional[str] = None, login: bool = False) -> Message:
    """Display main menu"""
    try:
        # Validate required state
        valid, error = validate_state(
            state_manager,
            {"channel", "authenticated"}
        )
        if not valid:
            raise ValueError(error)

        # Get channel info
        channel, error = get_channel_info(state_manager)
        if error:
            raise ValueError(error)

        # Validate auth flow
        if not auth_flow:
            raise ValueError("Auth flow not initialized")

        # Handle menu display based on state
        if login:
            logger.info(f"Showing post-login dashboard for channel {channel['identifier']}")
            return show_dashboard(state_manager, message="Login successful" if not message else message)

        if state_manager.get("authenticated"):
            logger.info(f"Showing authenticated dashboard for channel {channel['identifier']}")
            return show_dashboard(state_manager, message=message)

        # Show registration for unauthenticated users
        logger.info(f"Showing registration menu for channel {channel['identifier']}")
        return auth_flow.handle_registration(register=True)

    except ValueError as e:
        logger.error(f"Menu display error: {str(e)}")
        return create_error_message(state_manager, str(e))


def handle_hi(state_manager: Any, auth_flow: Any) -> Message:
    """Handle initial greeting"""
    try:
        # Validate required state
        valid, error = validate_state(
            state_manager,
            {"channel"}
        )
        if not valid:
            raise ValueError(error)

        # Get channel info
        channel, error = get_channel_info(state_manager)
        if error:
            raise ValueError(error)

        # Validate auth flow
        if not auth_flow:
            raise ValueError("Auth flow not initialized")

        # Log greeting event
        audit.log_flow_event(
            "auth_handler",
            "greeting",
            None,
            {"channel_id": channel["identifier"]},
            "in_progress"
        )

        logger.info(f"Processing greeting for channel {channel['identifier']}")

        # Always attempt login to refresh state
        success, _ = auth_flow.attempt_login()

        if success:
            logger.info(f"Login successful for channel {channel['identifier']}")
            return handle_menu(state_manager, auth_flow, login=True)

        logger.info(f"Showing registration for new user on channel {channel['identifier']}")
        return auth_flow.handle_registration(register=True)

    except ValueError as e:
        logger.error(f"Greeting error: {str(e)}")
        return create_error_message(state_manager, str(e))


def handle_refresh(state_manager: Any, auth_flow: Any) -> Message:
    """Handle dashboard refresh"""
    try:
        # Validate required state
        valid, error = validate_state(
            state_manager,
            {"channel"}
        )
        if not valid:
            raise ValueError(error)

        # Get channel info
        channel, error = get_channel_info(state_manager)
        if error:
            raise ValueError(error)

        # Log refresh event
        audit.log_flow_event(
            "auth_handler",
            "refresh",
            None,
            {"channel_id": channel["identifier"]},
            "in_progress"
        )

        logger.info(f"Refreshing dashboard for channel {channel['identifier']}")
        return handle_menu(state_manager, auth_flow, message="Dashboard refreshed")

    except ValueError as e:
        logger.error(f"Refresh error: {str(e)}")
        return create_error_message(state_manager, str(e))
