"""Action flow implementation enforcing SINGLE SOURCE OF TRUTH"""
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
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from services.credex.service import get_member_accounts
from ...member.dashboard import handle_dashboard_display

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

ACTION_TITLES = {
    "cancel": "Cancel",
    "accept": "Accept",
    "decline": "Decline"
}


def create_list_message(channel_id: str, flow_type: str) -> Message:
    """Create list message for action selection"""
    return Message(
        recipient=MessageRecipient(
            channel_id=ChannelIdentifier(
                channel=ChannelType.WHATSAPP,
                value=channel_id
            )
        ),
        content=InteractiveContent(
            interactive_type=InteractiveType.LIST,
            body=f"Select an offer to {flow_type.lower()}:"
        )
    )


def create_confirmation_message(channel_id: str, credex_id: str, flow_type: str) -> Message:
    """Create confirmation message for action with buttons"""
    action_title = ACTION_TITLES.get(flow_type, flow_type.capitalize())
    return Message(
        recipient=MessageRecipient(
            channel_id=ChannelIdentifier(
                channel=ChannelType.WHATSAPP,
                value=channel_id
            )
        ),
        content=InteractiveContent(
            interactive_type=InteractiveType.BUTTON,
            body=f"Are you sure you want to {action_title.lower()} offer {credex_id}?",
            action_items={
                "buttons": [
                    {
                        "id": "confirm_action",
                        "title": f"Yes, {action_title}"
                    },
                    {
                        "id": "cancel_action",
                        "title": "No, Cancel"
                    }
                ]
            }
        )
    )


def get_list_message(state_manager: Any, flow_type: str) -> Message:
    """Get list message with strict state validation"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return create_list_message(channel["identifier"], flow_type)

    except StateException as e:
        logger.error(f"List message error: {str(e)}")
        raise


def validate_selection(selection: str, flow_type: str) -> bool:
    """Validate selection input"""
    return selection.startswith(f"{flow_type}_")


def store_selection(state_manager: Any, selection: str, flow_type: str) -> Tuple[bool, Optional[str]]:
    """Store validated selection in state"""
    try:
        # Extract credex ID
        credex_id = selection[len(flow_type) + 1:] if selection.startswith(f"{flow_type}_") else None
        if not credex_id:
            raise StateException("Invalid selection format")

        # Get flow data (StateManager validates)
        flow_data = state_manager.get("flow_data") or {}

        # Update state
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": flow_data.get("flow_type"),
                "step": flow_data.get("step", 0),
                "current_step": "confirm",
                "data": {
                    **flow_data.get("data", {}),
                    "selected_credex_id": credex_id
                }
            }
        })
        if not success:
            raise StateException(error)

        # Log success
        channel = state_manager.get("channel")
        logger.info(f"Stored credex ID {credex_id} for {flow_type} flow on channel {channel['identifier']}")
        return True, None

    except StateException as e:
        logger.error(f"Failed to store selection: {str(e)}")
        return False, str(e)


def get_confirmation_message(state_manager: Any, flow_type: str) -> Message:
    """Get confirmation message with strict state validation"""
    try:
        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        return create_confirmation_message(
            channel["identifier"],
            flow_data["data"]["selected_credex_id"],
            flow_type
        )

    except StateException as e:
        logger.error(f"Confirmation message error: {str(e)}")
        raise


def complete_action(state_manager: Any, flow_type: str) -> Tuple[bool, Dict[str, Any]]:
    """Complete action flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")
        credex_id = flow_data["data"]["selected_credex_id"]

        # Log attempt
        audit.log_flow_event(
            f"{flow_type}_flow",
            f"{flow_type}_attempt",
            None,
            {
                "channel_id": channel["identifier"],
                "credex_id": credex_id
            },
            "attempt"
        )

        # Make API call using pure functions
        success, response = get_member_accounts(state_manager)
        if not success:
            error_msg = response.get("message", f"Failed to {flow_type} offer")
            logger.error(f"API call failed: {error_msg} for channel {channel['identifier']}")
            return False, {"message": error_msg}

        # Update dashboard
        try:
            handle_dashboard_display(state_manager, success_message=f"Successfully {flow_type}ed offer")
        except StateException as err:
            logger.error(f"Failed to update dashboard: {str(err)}")

        # Log success
        audit.log_flow_event(
            f"{flow_type}_flow",
            f"{flow_type}_success",
            None,
            {
                "channel_id": channel["identifier"],
                "credex_id": credex_id
            },
            "success"
        )

        logger.info(f"Successfully completed {flow_type} flow for channel {channel['identifier']}")

        return True, {
            "success": True,
            "message": f"Successfully {flow_type}ed credex offer",
            "response": response
        }

    except StateException as e:
        logger.error(f"Failed to complete {flow_type}: {str(e)}")
        return False, {"message": str(e)}


def process_action_step(
    state_manager: Any,
    step: str,
    flow_type: str,
    input_data: Any = None
) -> Message:
    """Process action step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Handle each step
        if step == "select":
            if input_data:
                if not validate_selection(input_data, flow_type):
                    raise StateException("Invalid selection")
                success, error = store_selection(state_manager, input_data, flow_type)
                if not success:
                    raise StateException(error)
                return get_confirmation_message(state_manager, flow_type)
            return get_list_message(state_manager, flow_type)

        elif step == "confirm":
            if (input_data and
                input_data.get("type") == "interactive" and
                input_data.get("interactive", {}).get("type") == "button_reply" and
                    input_data.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"):
                success, response = complete_action(state_manager, flow_type)
                if not success:
                    raise StateException(response["message"])
                channel = state_manager.get("channel")
                return Message(
                    recipient=MessageRecipient(
                        channel_id=ChannelIdentifier(
                            channel=ChannelType.WHATSAPP,
                            value=channel["identifier"]
                        )
                    ),
                    content=InteractiveContent(
                        interactive_type=InteractiveType.LIST,
                        body=f"✅ Successfully {flow_type}ed offer!"
                    )
                )
            return get_confirmation_message(state_manager, flow_type)

        else:
            raise StateException(f"Invalid {flow_type} step: {step}")

    except StateException as e:
        logger.error(f"Action step error: {str(e)}")
        raise


def process_cancel_step(
    state_manager: Any,
    step: str,
    input_data: Any = None
) -> Message:
    """Process cancel step enforcing SINGLE SOURCE OF TRUTH"""
    return process_action_step(state_manager, step, "cancel", input_data)


def process_accept_step(
    state_manager: Any,
    step: str,
    input_data: Any = None
) -> Message:
    """Process accept step enforcing SINGLE SOURCE OF TRUTH"""
    return process_action_step(state_manager, step, "accept", input_data)


def process_decline_step(
    state_manager: Any,
    step: str,
    input_data: Any = None
) -> Message:
    """Process decline step enforcing SINGLE SOURCE OF TRUTH"""
    return process_action_step(state_manager, step, "decline", input_data)
