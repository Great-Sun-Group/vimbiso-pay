"""Authentication flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
from services.credex.auth import login

logger = logging.getLogger(__name__)


def handle_registration(state_manager: Any) -> Message:
    """Handle registration flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        channel = state_manager.get("channel")

        # Set registration flow state
        state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "welcome",
                "type": "registration_welcome",
                "data": {
                    "channel_id": channel["identifier"]
                }
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
                error_type="flow",
                message="Unable to process registration. Please try again.",
                step_id="welcome",
                details={
                    "flow_type": "registration",
                    "operation": "registration_start"
                }
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
        # Update flow state for login attempt
        state_manager.update_state({
            "flow_data": {
                "flow_type": "auth",
                "step": 0,
                "current_step": "login",
                "data": {
                    "type": "login_attempt",
                    "data": {}
                }
            }
        })

        # Attempt login
        success, response = login(state_manager)
        if not success:
            # Let error propagate up with flow context
            error_context = ErrorContext(
                error_type="flow",
                message="Login failed",
                step_id="login",
                details={
                    "flow_type": "auth",
                    "operation": "login_attempt",
                    "response": response
                }
            )
            return False, ErrorHandler.handle_error(
                StateException("Login failed"),
                state_manager,
                error_context
            )

        # Update flow state with response
        state_manager.update_state({
            "flow_data": {
                "flow_type": "auth",
                "step": 1,
                "current_step": "login_complete",
                "type": "login_response",
                "data": response
            }
        })

        return True, response

    except Exception as e:
        # Add flow context to any error
        error_context = ErrorContext(
            error_type="flow",
            message="Login failed",
            step_id="login",
            details={
                "flow_type": "auth",
                "operation": "login_attempt",
                "error": str(e)
            }
        )
        return False, ErrorHandler.handle_error(e, state_manager, error_context)
