"""Authentication flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.error_handler import handle_flow_error
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
        # Use central error handler
        _, error_response = handle_flow_error(
            state_manager,
            e,
            flow_type="registration",
            step_id="welcome"
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
                body="❌ Error: Unable to process registration. Please try again."
            ),
            metadata=error_response["data"]["action"]["details"]
        )


def attempt_login(state_manager: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Attempt login enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Attempt login
        success, response = handle_login(state_manager)
        if not success:
            return handle_flow_error(
                state_manager,
                Exception(response.get("message", "Login failed")),
                flow_type="auth",
                step_id="login"
            )

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
            return handle_flow_error(
                state_manager,
                Exception(error),
                flow_type="dashboard",
                step_id="display"
            )

        # All data is in state, no need to return response
        return True, None

    except (StateException, KeyError) as e:
        return handle_flow_error(
            state_manager,
            e,
            flow_type="auth",
            step_id="login"
        )
