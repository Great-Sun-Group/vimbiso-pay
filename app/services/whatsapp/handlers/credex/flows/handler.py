"""Core message handling for credex flows using component system"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.types import (
    ButtonContent,
    ChannelIdentifier,
    ChannelType,
    Message,
    MessageRecipient,
    TextContent
)
from core.utils.exceptions import ComponentException, FlowException, SystemException

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
    """Validate message structure

    Raises:
        ComponentException: If message validation fails
    """
    # Validate required fields
    required_fields = ["type", "timestamp", "content"]
    missing = [field for field in required_fields if field not in message]
    if missing:
        raise ComponentException(
            message=f"Missing required message fields: {', '.join(missing)}",
            component="message_handler",
            field="message",
            value=str(message)
        )

    # Validate message data
    message_type = message.get("type")
    if not message_type:
        raise ComponentException(
            message="Missing message type",
            component="message_handler",
            field="type",
            value=str(message)
        )

    message_content = message.get("content", {})
    if not message_content:
        raise ComponentException(
            message="Missing message content",
            component="message_handler",
            field="content",
            value=str(message)
        )


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Message:
    """Handle incoming message with proper validation

    Raises:
        ComponentException: For message validation errors
        FlowException: For flow state/type errors
        SystemException: For infrastructure errors
    """
    try:
        # Validate message structure
        validate_message_state(state_manager, message)

        # Get flow state
        flow_state = state_manager.get_flow_state()
        if not flow_state:
            raise FlowException(
                message="No active flow",
                step="unknown",
                action="handle_message",
                data={"message": message}
            )

        # Get channel ID
        channel_id = state_manager.get_channel_id()

        # Check if already complete
        if flow_state.get("current_step") == "complete":
            return create_message(channel_id, "✅ Your request has been processed.")

        # Validate flow type
        flow_type = flow_state.get("flow_type")
        if not flow_type:
            raise FlowException(
                message="Missing flow type",
                step=flow_state.get("current_step"),
                action="validate_flow",
                data=flow_state
            )

        # Process message through appropriate handler
        if flow_type == "offer":
            from . import offer
            response = offer.process_offer_step(
                state_manager,
                flow_state["current_step"],
                message.get("text", {}).get("body", "")
            )
        else:
            from . import action
            if flow_type == "accept":
                response = action.process_accept_step(state_manager, flow_state["current_step"], message)
            elif flow_type == "decline":
                response = action.process_decline_step(state_manager, flow_state["current_step"], message)
            elif flow_type == "cancel":
                response = action.process_cancel_step(state_manager, flow_state["current_step"], message)
            else:
                raise FlowException(
                    message=f"Unknown flow type: {flow_type}",
                    step=flow_state.get("current_step"),
                    action="process_flow",
                    data={"flow_type": flow_type}
                )

        # Check completion
        if flow_state.get("current_step") == "complete":
            logger.info(
                "Flow completed successfully",
                extra={
                    "flow_type": flow_type,
                    "channel_id": channel_id,
                    "final_data": flow_state.get("data", {})
                }
            )
            return create_message(channel_id, "✅ Your request has been processed.")

        return response

    except (ComponentException, FlowException):
        # Let validation/flow errors propagate up
        raise

    except Exception as e:
        # Wrap unexpected errors as system errors
        raise SystemException(
            message=f"Failed to process message: {str(e)}",
            code="MESSAGE_ERROR",
            service="message_handler",
            action="handle_message"
        )
