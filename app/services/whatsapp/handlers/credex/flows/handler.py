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
    
    # Validate message structure without modifying flow state
    if not message.get("type"):
        raise StateException("Missing message type")
    if not message.get("timestamp"):
        raise StateException("Missing message timestamp")
    if not message.get("content"):
        raise StateException("Missing message content")

    # Only update state if validation passes
    state_manager.update_state({
        "message_data": {  # Separate from flow_data
            "type": message.get("type"),
            "timestamp": message.get("timestamp"),
            "content": message.get("content", {})
        }
    })


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Message:
    """Handle incoming message through state validation"""
    # Initialize tracking variables
    error_type = "flow"
    flow_data = None

    try:
        # Validate message state
        validate_message_state(state_manager, message)

        # Get flow data and channel ID
        flow_data = state_manager.get_flow_data()
        channel_id = state_manager.get("channel")["identifier"]

        # Check if already complete
        if flow_data.get("current_step") == "complete":
            return create_message(channel_id, "✅ Your request has been processed.")

        # Validate required flow data
        if not flow_data.get("flow_type"):
            raise StateException("Missing flow type")
        if not flow_data.get("current_step"):
            raise StateException("Missing current step")

        # Process message through appropriate handler
        if flow_data["flow_type"] == "offer":
            from . import offer
            response = offer.process_offer_step(
                state_manager,
                flow_data["current_step"],  # Required field, will raise if missing
                message.get("text", {}).get("body", "")
            )
        else:
            from . import action
            if flow_data["flow_type"] == "accept":
                response = action.process_accept_step(state_manager, flow_data["current_step"], message)
            elif flow_data["flow_type"] == "decline":
                response = action.process_decline_step(state_manager, flow_data["current_step"], message)
            elif flow_data["flow_type"] == "cancel":
                response = action.process_cancel_step(state_manager, flow_data["current_step"], message)
            else:
                raise StateException(f"Unknown flow type: {flow_data['flow_type']}")

        # Check if complete after processing
        updated_flow_data = state_manager.get_flow_data()
        if updated_flow_data.get("current_step") == "complete":
            # Get final step data for logging
            final_step_data = state_manager.get_flow_step_data()
            logger.info(
                "Flow completed successfully",
                extra={
                    "flow_type": updated_flow_data.get("flow_type"),
                    "channel_id": channel_id,
                    "steps_taken": updated_flow_data.get("step", 0),
                    "final_data": final_step_data
                }
            )
            return create_message(channel_id, "✅ Your request has been processed.")

        return response

    except Exception as e:
        # Create error context with proper step tracking
        error_context = ErrorContext(
            error_type=error_type,
            message="Failed to process message",
            step_id=flow_data.get("current_step") if flow_data else None,
            details={
                "message_type": message.get("type"),
                "flow_type": flow_data.get("flow_type") if flow_data else None,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
