"""Authentication flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.error_handler import ErrorHandler, ErrorContext
from services.credex.service import handle_login

logger = logging.getLogger(__name__)


def handle_registration(state_manager: Any) -> Message:
    """Handle registration flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        channel = state_manager.get("channel")

        # Initialize registration flow through state update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "welcome",
                "data": {}
            }
        })

        # Return welcome message with registration button
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
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

    except StateException as e:
        # Use ErrorHandler with context
        error_response = ErrorHandler.handle_error(
            e,
            state_manager,
            ErrorContext(
                error_type="registration",
                message="Unable to process registration. Please try again.",
                step_id="welcome",
                details={"flow_type": "registration"}
            )
        )

        # Convert error response to Message
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=state_manager.get("channel")["identifier"]
                )
            ),
            content=TextContent(
                body=f"❌ Error: {error_response['data']['action']['details']['message']}"
            ),
            metadata=error_response["data"]["action"]["details"]
        )


def attempt_login(state_manager: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Attempt login enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Attempt login
        success, response = handle_login(state_manager)
        if not success:
            error_context = ErrorContext(
                error_type="auth",
                message=response.get("message", "Login failed"),
                step_id="login",
                details={"flow_type": "auth"}
            )
            error_response = ErrorHandler.handle_error(
                Exception(error_context.message),
                state_manager,
                error_context
            )
            return False, error_response

        # Service layer handled member state updates including account data
        # Update flow state to show dashboard
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "dashboard",
                "step": 0,
                "current_step": "display",
                "data": {}
            }
        })

        if not success:
            error_context = ErrorContext(
                error_type="dashboard",
                message=str(error),
                step_id="display",
                details={"flow_type": "dashboard"}
            )
            error_response = ErrorHandler.handle_error(
                Exception(error_context.message),
                state_manager,
                error_context
            )
            return False, error_response

        # All data is in state, no need to return response
        return True, None

    except (StateException, KeyError) as e:
        error_context = ErrorContext(
            error_type="auth",
            message=str(e),
            step_id="login",
            details={"flow_type": "auth"}
        )
        error_response = ErrorHandler.handle_error(
            e,
            state_manager,
            error_context
        )
        return False, error_response
