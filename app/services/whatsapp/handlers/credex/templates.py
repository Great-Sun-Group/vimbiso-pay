"""Message templates enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict, List, Optional

from core.messaging.types import (Button, ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)


def create_message(state_manager: Any, text: str, buttons: Optional[List[Dict[str, str]]] = None) -> Message:
    """Create message with proper state validation"""
    # Let StateManager validate channel and member
    state_manager.update_state({
        "validation": {
            "type": "message_context",
            "required": ["channel", "member"]
        }
    })

    # Get validated data
    channel_id = state_manager.get_channel_id()

    recipient = MessageRecipient(
        channel_id=ChannelIdentifier(
            channel=ChannelType.WHATSAPP,
            value=channel_id
        )
    )

    if buttons:
        # Convert button dicts to Button objects
        button_objects = [
            Button(id=btn["id"], title=btn["text"])
            for btn in buttons
        ]
        return Message(
            recipient=recipient,
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=text,
                buttons=button_objects
            )
        )

    return Message(
        recipient=recipient,
        content=TextContent(body=text)
    )


def create_list_message(state_manager: Any, items: List[Dict[str, Any]] = None) -> Message:
    """Create list selection message with proper state validation"""
    # Let StateManager validate channel and member
    state_manager.update_state({
        "validation": {
            "type": "message_context",
            "required": ["channel", "member"]
        }
    })

    # Let StateManager validate flow state
    state_manager.update_state({
        "validation": {
            "type": "flow_state"
        }
    })

    # Get validated flow state
    flow_state = state_manager.get_flow_state()
    flow_type = flow_state.get("flow_type", "offer")

    if not items:
        return create_message(
            state_manager,
            f"No {flow_type} items available"
        )

    message_parts = [f"Select {flow_type} item:\n"]
    for i, item in enumerate(items, 1):
        amount = item.get("formattedAmount", "Unknown amount")
        counterparty = item.get("counterpartyName", "Unknown")
        message_parts.append(f"{i}. {amount} with {counterparty}")

    return create_message(state_manager, "\n".join(message_parts))


def create_confirmation_message(state_manager: Any, item_id: str) -> Message:
    """Create confirmation message with proper state validation"""
    # Let StateManager validate channel and member
    state_manager.update_state({
        "validation": {
            "type": "message_context",
            "required": ["channel", "member"]
        }
    })

    # Let StateManager validate flow state
    state_manager.update_state({
        "validation": {
            "type": "flow_state"
        }
    })

    # Get validated flow state
    flow_state = state_manager.get_flow_state()
    flow_type = flow_state.get("flow_type", "offer")

    return create_message(
        state_manager,
        f"Confirm {flow_type}:\n"
        f"Item ID: {item_id}\n\n"
        "Please confirm (yes/no):"
    )


def create_error_message(state_manager: Any, error_msg: str) -> Message:
    """Create error message with proper state validation"""
    # Let StateManager validate channel and member
    state_manager.update_state({
        "validation": {
            "type": "message_context",
            "required": ["channel", "member"]
        }
    })

    return create_message(
        state_manager,
        f"❌ Error: {error_msg}"
    )


def create_success_message(state_manager: Any, success_msg: str) -> Message:
    """Create success message with proper state validation"""
    # Let StateManager validate channel and member
    state_manager.update_state({
        "validation": {
            "type": "message_context",
            "required": ["channel", "member"]
        }
    })

    return create_message(
        state_manager,
        f"✅ {success_msg}"
    )
