"""Action flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (
    ChannelIdentifier,
    ChannelType,
    InteractiveContent,
    InteractiveType,
    Message,
    MessageRecipient,
    WhatsAppMessage
)
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...member.dashboard import handle_dashboard_display

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

REQUIRED_FIELDS = {"channel", "member_id", "account_id", "authenticated", "jwt_token"}

ACTION_TITLES = {
    "cancel": "Cancel",
    "accept": "Accept",
    "decline": "Decline"
}


def create_list_message(channel_id: str, flow_type: str) -> Message:
    """Create list message for action selection"""
    return WhatsAppMessage.create_text(
        channel_id,
        f"Select an offer to {flow_type.lower()}:"
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
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        channel = state_manager.get("channel")
        return create_list_message(channel["identifier"], flow_type)

    except ValueError as e:
        return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")


def validate_selection(selection: str, flow_type: str) -> bool:
    """Validate selection input"""
    return selection.startswith(f"{flow_type}_")


def store_selection(state_manager: Any, selection: str, flow_type: str) -> Tuple[bool, Optional[str]]:
    """Store validated selection in state"""
    try:
        # Extract credex ID
        credex_id = selection[len(flow_type) + 1:] if selection.startswith(f"{flow_type}_") else None
        if not credex_id:
            return False, "Invalid selection format"

        # Get flow data (SINGLE SOURCE OF TRUTH)
        flow_data = state_manager.get("flow_data")
        if not isinstance(flow_data, dict):
            flow_data = {}

        # Update state (validation handled by state manager)
        new_flow_data = {
            **flow_data,
            "selected_credex_id": credex_id,
            "current_step": "confirm"
        }

        success, error = state_manager.update({"flow_data": new_flow_data})
        if not success:
            return False, error

        # Log success
        channel = state_manager.get("channel")
        logger.info(f"Stored credex ID {credex_id} for {flow_type} flow on channel {channel['identifier']}")
        return True, None

    except Exception as e:
        logger.error(f"Failed to store selection: {str(e)}")
        return False, str(e)


def get_confirmation_message(state_manager: Any, flow_type: str) -> Message:
    """Get confirmation message with strict state validation"""
    try:
        # Get required data (validation handled by flow steps)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")
        if not flow_data:
            raise ValueError("Missing flow data")

        return create_confirmation_message(
            channel["identifier"],
            flow_data["selected_credex_id"],
            flow_type
        )

    except ValueError as e:
        return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")


def complete_action(state_manager: Any, credex_service: Any, flow_type: str) -> Tuple[bool, Dict[str, Any]]:
    """Complete action flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (already validated)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")
        if not flow_data:
            raise ValueError("Missing flow data")

        credex_id = flow_data["selected_credex_id"]

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

        # Make API call
        success, response = getattr(credex_service, f"{flow_type}_credex")(credex_id)
        if not success:
            error_msg = response.get("message", f"Failed to {flow_type} offer")
            logger.error(f"API call failed: {error_msg} for channel {channel['identifier']}")
            return False, {"message": error_msg}

        # Update dashboard
        try:
            handle_dashboard_display(state_manager, credex_service, f"Successfully {flow_type}ed offer")
        except ValueError as err:
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

    except Exception as e:
        logger.error(f"Failed to complete {flow_type}: {str(e)}")
        return False, {"message": str(e)}


def process_action_step(
    state_manager: Any,
    step: str,
    flow_type: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Message:
    """Process action step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {field: state_manager.get(field) for field in REQUIRED_FIELDS},
            REQUIRED_FIELDS
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Handle each step
        if step == "select":
            if input_data:
                if not validate_selection(input_data, flow_type):
                    raise ValueError("Invalid selection")
                success, error = store_selection(state_manager, input_data, flow_type)
                if not success:
                    raise ValueError(error)
                return get_confirmation_message(state_manager, flow_type)
            return get_list_message(state_manager, flow_type)

        elif step == "confirm":
            if not credex_service:
                raise ValueError("CredEx service required for confirmation")

            if (input_data and
                input_data.get("type") == "interactive" and
                input_data.get("interactive", {}).get("type") == "button_reply" and
                    input_data.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"):
                success, response = complete_action(state_manager, credex_service, flow_type)
                if not success:
                    raise ValueError(response["message"])
                return WhatsAppMessage.create_text(
                    state_manager.get("channel")["identifier"],
                    f"✅ Successfully {flow_type}ed offer!"
                )
            return get_confirmation_message(state_manager, flow_type)

        else:
            raise ValueError(f"Invalid {flow_type} step: {step}")

    except ValueError as e:
        return WhatsAppMessage.create_text(
            state_manager.get("channel", {}).get("identifier", "unknown"),
            f"Error: {str(e)}"
        )


def process_cancel_step(
    state_manager: Any,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Message:
    """Process cancel step enforcing SINGLE SOURCE OF TRUTH"""
    return process_action_step(state_manager, step, "cancel", input_data, credex_service)


def process_accept_step(
    state_manager: Any,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Message:
    """Process accept step enforcing SINGLE SOURCE OF TRUTH"""
    return process_action_step(state_manager, step, "accept", input_data, credex_service)


def process_decline_step(
    state_manager: Any,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Message:
    """Process decline step enforcing SINGLE SOURCE OF TRUTH"""
    return process_action_step(state_manager, step, "decline", input_data, credex_service)
