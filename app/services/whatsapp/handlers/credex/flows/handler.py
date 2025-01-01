"""Core message handling for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.types import (ButtonContent, ChannelIdentifier,
                                  ChannelType, Message, MessageRecipient,
                                  TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)


def create_message(channel_id: str, text: str, buttons: Optional[List[Dict[str, str]]] = None) -> Message:
    """Create core message type with optional buttons"""
    recipient = MessageRecipient(
        channel_id=ChannelIdentifier(
            channel=ChannelType.WHATSAPP,
            value=channel_id
        )
    )

    if buttons:
        return Message(
            recipient=recipient,
            content=ButtonContent(body=text, buttons=buttons)
        )

    return Message(
        recipient=recipient,
        content=TextContent(body=text)
    )


def validate_message_state(state_manager: Any, message: Dict[str, Any]) -> None:
    """Validate message through state manager"""

    # Let StateManager validate message structure
    state_manager.update_state({
        "validation": {
            "type": "message_structure",
            "required_fields": ["type", "timestamp", "content"],
            "message": message
        }
    })

    # Let StateManager validate message data
    state_manager.update_state({
        "validation": {
            "type": "message_data",
            "message_type": message.get("type"),
            "message_timestamp": message.get("timestamp"),
            "message_content": message.get("content", {})
        }
    })


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Message:
    """Handle incoming message through state validation"""
    # Initialize tracking variables
    error_type = "flow"
    flow_state = None

    try:
        # Validate message state
        validate_message_state(state_manager, message)

        # Let StateManager validate flow state
        state_manager.update_state({
            "validation": {
                "type": "flow_state"
            }
        })

        # Get validated flow and channel data
        flow_state = state_manager.get_flow_state()
        channel_id = state_manager.get_channel_id()

        # Check if already complete
        if flow_state.get("current_step") == "complete":
            return create_message(channel_id, "✅ Your request has been processed.")

        # Let StateManager validate flow type
        state_manager.update_state({
            "validation": {
                "type": "flow_type",
                "required": True
            }
        })

        # Process message through appropriate handler
        if flow_state["flow_type"] == "offer":
            from . import offer
            response = offer.process_offer_step(
                state_manager,
                flow_state["current_step"],
                message.get("text", {}).get("body", "")
            )
        else:
            from . import action
            if flow_state["flow_type"] == "accept":
                response = action.process_accept_step(state_manager, flow_state["current_step"], message)
            elif flow_state["flow_type"] == "decline":
                response = action.process_decline_step(state_manager, flow_state["current_step"], message)
            elif flow_state["flow_type"] == "cancel":
                response = action.process_cancel_step(state_manager, flow_state["current_step"], message)
            else:
                raise StateException(f"Unknown flow type: {flow_state['flow_type']}")

        # Let StateManager validate completion state
        state_manager.update_state({
            "validation": {
                "type": "flow_complete",
                "check_completion": True
            }
        })

        # Get validated completion state
        completion_state = state_manager.get_flow_complete_data()
        if completion_state.get("is_complete"):
            logger.info(
                "Flow completed successfully",
                extra={
                    "flow_type": completion_state.get("flow_type"),
                    "channel_id": channel_id,
                    "steps_taken": completion_state.get("steps_taken", 0),
                    "final_data": completion_state.get("final_data")
                }
            )
            return create_message(channel_id, "✅ Your request has been processed.")

        return response

    except Exception as e:
        # Create error context with proper step tracking
        error_context = ErrorContext(
            error_type=error_type,
            message="Failed to process message",
            step_id=flow_state.get("current_step") if flow_state else None,
            details={
                "message_type": message.get("type"),
                "flow_type": flow_state.get("flow_type") if flow_state else None,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
