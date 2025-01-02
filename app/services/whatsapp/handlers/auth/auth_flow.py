"""Authentication flow implementation using component system"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (
    ChannelIdentifier,
    ChannelType,
    InteractiveContent,
    InteractiveType,
    Message,
    MessageRecipient
)
from core.messaging.flow import FlowManager, initialize_flow
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException, SystemException

logger = logging.getLogger(__name__)


def handle_registration(state_manager: Any) -> Message:
    """Initialize registration flow using component system"""
    try:
        # Initialize registration flow
        initialize_flow(state_manager, "registration", "welcome")

        # Get channel for message
        channel_id = state_manager.get_channel_id()

        # Return welcome message
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body="Welcome to VimbisoPay 💰\n\nWe're your portal 🚪to the credex ecosystem 🌱\n\nBecome a member 🌐 and open a free account 💳 to get started 📈",
                action_items={
                    "buttons": [{
                        "type": "reply",
                        "reply": {
                            "id": "start_registration",
                            "title": "Become a Member"
                        }
                    }]
                }
            )
        )

    except (ComponentException, FlowException, SystemException) as e:
        return ErrorHandler.handle_error_with_message(e, state_manager)


def attempt_login(state_manager: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Attempt login using component system"""
    try:
        # Initialize auth flow
        initialize_flow(state_manager, "auth", "login")

        # Get login component and process
        flow_manager = FlowManager("auth")
        login_component = flow_manager.get_component("login")

        # Set state manager context
        login_component.state_manager = state_manager

        # Process login
        result = login_component.to_verified_data(None)  # Login triggered by "hi"

        # Update flow state with result
        state_manager.update_state({
            "flow_data": {
                "step": "login_complete",
                "data": result
            }
        })

        return True, result

    except ComponentException as e:
        # Login validation failed
        logger.error(f"Login validation error: {str(e)}")
        return False, ErrorHandler.handle_component_error(
            component=e.details["component"],
            field=e.details["field"],
            value=e.details["value"],
            message=str(e)
        )
    except FlowException as e:
        # Flow state error
        logger.error(f"Login flow error: {str(e)}")
        return False, ErrorHandler.handle_flow_error(
            step=e.details["step"],
            action=e.details["action"],
            data=e.details["data"],
            message=str(e)
        )
    except Exception as e:
        # System error
        logger.error(f"Login system error: {str(e)}")
        return False, ErrorHandler.handle_system_error(
            code="LOGIN_ERROR",
            service="auth_flow",
            action="attempt_login",
            message="Unexpected error during login"
        )
