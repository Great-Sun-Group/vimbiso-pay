"""Action flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
from services.credex.service import get_credex_service

from .steps import process_step

logger = logging.getLogger(__name__)


def create_message(channel_id: str, text: str) -> Message:
    """Create core message type"""
    return Message(
        recipient=MessageRecipient(
            channel_id=ChannelIdentifier(
                channel=ChannelType.WHATSAPP,
                value=channel_id
            )
        ),
        content=TextContent(body=text)
    )


def create_list_message(channel_id: str, action: str, items: List[Dict[str, Any]] = None) -> Message:
    """Create list selection message"""
    if not items:
        return create_message(
            channel_id,
            f"No {action} offers available"
        )

    message_parts = [f"Select offer to {action}:\n"]
    for i, item in enumerate(items, 1):
        amount = item.get("formattedInitialAmount", "Unknown amount")
        counterparty = item.get("counterpartyAccountName", "Unknown")
        message_parts.append(f"{i}. {amount} with {counterparty}")

    return create_message(channel_id, "\n".join(message_parts))


def create_action_confirmation(channel_id: str, credex_id: str, action: str) -> Message:
    """Create action confirmation message"""
    return create_message(
        channel_id,
        f"Confirm {action}:\n"
        f"CredEx ID: {credex_id}\n\n"
        "Please confirm (yes/no):"
    )


def process_action_step(state_manager: Any, step: str, action: str, input_data: Any = None) -> Message:
    """Process action step with validation"""
    try:
        # Get channel ID through state manager
        channel_id = state_manager.get("channel")["identifier"]

        # Process step input through generic step processor
        result = process_step(state_manager, step, input_data, action)

        # Initial prompts or responses based on step
        if step == "select":
            if not input_data:
                return create_list_message(channel_id, action)

            # Show confirmation with credex ID
            return create_action_confirmation(
                channel_id,
                result["credex_id"],
                action
            )

        elif step == "confirm":
            if not input_data:
                # Re-show confirmation with current data
                state = state_manager.get_flow_step_data()
                return create_action_confirmation(
                    channel_id,
                    state["credex_id"],
                    action
                )

            # Process confirmation result
            if result["confirmed"]:
                # Submit action through credex service
                credex_service = get_credex_service(state_manager)
                success, response = credex_service[f"{action}_credex"](
                    state_manager.get_flow_step_data()
                )
                if not success:
                    raise StateException(response.get("message", "Failed to create offer"))

                # Log success
                logger.info(
                    f"Action {action} completed",
                    extra={
                        "channel_id": channel_id,
                        "response": response
                    }
                )
                return create_message(channel_id, "✅ Your request has been processed.")

            # Not confirmed - show confirmation again
            state = state_manager.get_flow_step_data()
            return create_action_confirmation(
                channel_id,
                state["credex_id"],
                action
            )

        raise StateException(f"Invalid step: {step}")

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id=step,
            details={
                "action": action,
                "input": input_data
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def process_cancel_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process cancel step"""
    return process_action_step(state_manager, step, "cancel", input_data)


def process_accept_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process accept step"""
    return process_action_step(state_manager, step, "accept", input_data)


def process_decline_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process decline step"""
    return process_action_step(state_manager, step, "decline", input_data)
