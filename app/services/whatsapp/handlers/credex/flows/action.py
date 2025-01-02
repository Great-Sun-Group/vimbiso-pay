"""Action flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import FlowException, SystemException
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
        # Let StateManager validate channel
        state_manager.update_state({
            "validation": {
                "type": "channel",
                "required": True
            }
        })

        # Get validated channel data
        channel_id = state_manager.get_channel_id()

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
                # Let StateManager validate flow state
                state_manager.update_state({
                    "validation": {
                        "type": "flow_state",
                        "step": "confirm",
                        "action": action
                    }
                })

                # Get validated flow state
                flow_state = state_manager.get_flow_state()
                return create_action_confirmation(
                    channel_id,
                    flow_state["credex_id"],
                    action
                )

            # Process confirmation result
            if result["confirmed"]:
                # Let StateManager validate action request
                state_manager.update_state({
                    "validation": {
                        "type": "action_request",
                        "action": action
                    }
                })

                # Submit action through credex service
                credex_service = get_credex_service(state_manager)
                success, response = credex_service[f"{action}_credex"](state_manager)

                if not success:
                    raise SystemException(
                        message=response.get("message", f"Failed to {action} offer"),
                        code=f"{action.upper()}_ERROR",
                        service="credex_action",
                        action=action
                    )

                # Log success
                logger.info(
                    f"Action {action} completed",
                    extra={
                        "channel_id": channel_id,
                        "response": response
                    }
                )
                return create_message(channel_id, "✅ Your request has been processed.")

            # Not confirmed - let StateManager validate flow state
            state_manager.update_state({
                "validation": {
                    "type": "flow_state",
                    "step": "confirm",
                    "action": action
                }
            })

            # Get validated flow state
            flow_state = state_manager.get_flow_state()
            return create_action_confirmation(
                channel_id,
                flow_state["credex_id"],
                action
            )

        raise FlowException(
            message=f"Invalid step: {step}",
            step=step,
            action="validate_step",
            data={"action": action}
        )

    except (FlowException, SystemException):
        # Let flow and system errors propagate up
        raise

    except Exception as e:
        # Wrap unexpected errors as system errors
        raise SystemException(
            message=str(e),
            code="ACTION_ERROR",
            service="credex_action",
            action=action,
            details={
                "step": step,
                "input": input_data
            }
        )


def process_cancel_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process cancel step"""
    return process_action_step(state_manager, step, "cancel", input_data)


def process_accept_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process accept step"""
    return process_action_step(state_manager, step, "accept", input_data)


def process_decline_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process decline step"""
    return process_action_step(state_manager, step, "decline", input_data)
