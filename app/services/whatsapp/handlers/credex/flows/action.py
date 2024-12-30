"""Action flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import (
    ChannelIdentifier,
    ChannelType,
    InteractiveContent,
    InteractiveType,
    Message,
    MessageRecipient
)
from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException
from services.credex.service import get_member_accounts
from ...member.dashboard import handle_dashboard_display

logger = logging.getLogger(__name__)

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


def get_action_title(flow_type: str) -> str:
    """Get action title from flow type

    Args:
        flow_type: Type of flow

    Returns:
        Action title string

    Raises:
        StateException: If flow type is invalid
    """
    if flow_type not in ACTION_TITLES and flow_type not in {"registration", "upgrade"}:
        raise StateException(f"Invalid flow type: {flow_type}")
    return ACTION_TITLES.get(flow_type, flow_type.capitalize())


def get_list_message(state_manager: Any, flow_type: str) -> Message:
    """Get list message with strict state validation"""
    try:
        # Let StateManager validate channel access
        channel_id = state_manager.get("channel")["identifier"]  # StateManager validates
        return create_list_message(channel_id, flow_type)

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to create offer list. Please try again",
            step_id="select",
            details={
                "flow_type": flow_type,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def validate_selection(selection: str, flow_type: str) -> str:
    """Validate selection input

    Args:
        selection: Selection string to validate
        flow_type: Type of flow

    Returns:
        Extracted credex ID

    Raises:
        StateException: If validation fails
    """
    try:
        if not selection.startswith(f"{flow_type}_"):
            error_context = ErrorContext(
                error_type="input",
                message="Invalid selection format. Please select from the list",
                step_id="select",
                details={
                    "selection": selection,
                    "flow_type": flow_type
                }
            )
            raise StateException(error_context.message)

        credex_id = selection[len(flow_type) + 1:]
        if not credex_id:
            error_context = ErrorContext(
                error_type="input",
                message="Missing credex ID. Please select from the list",
                step_id="select",
                details={
                    "selection": selection,
                    "flow_type": flow_type
                }
            )
            raise StateException(error_context.message)

        return credex_id

    except StateException:
        raise
    except Exception as e:
        error_context = ErrorContext(
            error_type="input",
            message="Failed to validate selection. Please try again",
            step_id="select",
            details={
                "selection": selection,
                "flow_type": flow_type,
                "error": str(e)
            }
        )
        raise StateException(error_context.message)


def store_selection(state_manager: Any, selection: str, flow_type: str) -> None:
    """Store validated selection in state

    Args:
        state_manager: State manager instance
        selection: Selection string to validate and store
        flow_type: Type of flow

    Raises:
        StateException: If validation or storage fails
    """
    try:
        # Validate selection (raises StateException if invalid)
        credex_id = validate_selection(selection, flow_type)

        # Let StateManager validate and update state
        success, error = state_manager.update_state({
            "flow_data": {
                "current_step": "confirm",
                "data": {
                    "selected_credex_id": credex_id
                }
            }
        })
        if not success:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to save selection. Please try again",
                step_id="select",
                details={
                    "selection": selection,
                    "flow_type": flow_type,
                    "credex_id": credex_id,
                    "error": error
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException(error),
                state_manager,
                error_context
            ))

        # Log success
        logger.info(
            "Selection stored successfully",
            extra={
                "credex_id": credex_id,
                "flow_type": flow_type,
                "channel_id": state_manager.get("channel")["identifier"]
            }
        )

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to process selection. Please try again",
            step_id="select",
            details={
                "selection": selection,
                "flow_type": flow_type,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def get_confirmation_message(state_manager: Any, flow_type: str) -> Message:
    """Get confirmation message with strict state validation"""
    try:
        # Let StateManager validate all state access
        channel_id = state_manager.get("channel")["identifier"]  # StateManager validates
        credex_id = state_manager.get("flow_data")["data"]["selected_credex_id"]  # StateManager validates

        # Get action title (raises StateException if invalid)
        action_title = get_action_title(flow_type)

        return create_confirmation_message(
            channel_id,
            credex_id,
            action_title
        )

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to create confirmation message. Please try again",
            step_id="confirm",
            details={
                "flow_type": flow_type,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def complete_action(state_manager: Any, flow_type: str) -> Dict[str, Any]:
    """Complete action flow enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        flow_type: Type of flow

    Returns:
        API response data

    Raises:
        StateException: If action completion fails
    """
    try:
        # Let StateManager validate state access
        credex_id = state_manager.get("flow_data")["data"]["selected_credex_id"]  # StateManager validates
        channel_id = state_manager.get("channel")["identifier"]  # StateManager validates

        # Log attempt
        logger.info(
            f"Attempting {flow_type} action",
            extra={
                "flow_type": flow_type,
                "credex_id": credex_id,
                "channel_id": channel_id
            }
        )

        try:
            # Make API call (raises StateException if fails)
            response = get_member_accounts(state_manager)
        except Exception as e:
            error_context = ErrorContext(
                error_type="api",
                message=f"Failed to {flow_type} offer. Please try again",
                step_id="confirm",
                details={
                    "flow_type": flow_type,
                    "credex_id": credex_id,
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        try:
            # Update dashboard (raises StateException if fails)
            handle_dashboard_display(state_manager, success_message=f"Successfully {flow_type}ed offer")
        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to update dashboard. Please check your offers page",
                step_id="confirm",
                details={
                    "flow_type": flow_type,
                    "credex_id": credex_id,
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        # Log success
        logger.info(
            f"Successfully completed {flow_type} action",
            extra={
                "flow_type": flow_type,
                "credex_id": credex_id,
                "channel_id": channel_id,
                "response": response
            }
        )

        return {
            "success": True,
            "message": f"Successfully {flow_type}ed credex offer",
            "response": response
        }

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=f"Failed to complete {flow_type} action. Please try again",
            step_id="confirm",
            details={
                "flow_type": flow_type,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def process_action_step(
    state_manager: Any,
    step: str,
    flow_type: str,
    input_data: Any = None
) -> Message:
    """Process action step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Handle each step (StateManager validates state)
        if step == "select":
            if input_data:
                # Validate and store selection (raises StateException if invalid)
                store_selection(state_manager, input_data, flow_type)
                return get_confirmation_message(state_manager, flow_type)
            return get_list_message(state_manager, flow_type)

        elif step == "confirm":
            try:
                # Let StateManager validate input data structure
                success, error = state_manager.update_state({
                    "flow_data": {
                        "input": input_data
                    }
                })
                if not success:
                    error_context = ErrorContext(
                        error_type="state",
                        message="Failed to process confirmation. Please try again",
                        step_id="confirm",
                        details={
                            "flow_type": flow_type,
                            "error": error
                        }
                    )
                    raise StateException(ErrorHandler.handle_error(
                        StateException(error),
                        state_manager,
                        error_context
                    ))
            except Exception as e:
                error_context = ErrorContext(
                    error_type="state",
                    message="Failed to save confirmation. Please try again",
                    step_id="confirm",
                    details={
                        "flow_type": flow_type,
                        "input": input_data,
                        "error": str(e)
                    }
                )
                raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

            if (input_data and
                input_data.get("type") == "interactive" and
                input_data.get("interactive", {}).get("type") == "button_reply" and
                    input_data.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"):
                # Complete action (raises StateException if fails)
                complete_action(state_manager, flow_type)
                return Message(
                    recipient=MessageRecipient(
                        channel_id=ChannelIdentifier(
                            channel=ChannelType.WHATSAPP,
                            value=state_manager.get("channel")["identifier"]  # StateManager validates
                        )
                    ),
                    content=InteractiveContent(
                        interactive_type=InteractiveType.LIST,
                        body=f"✅ Successfully {flow_type}ed offer!"
                    )
                )
            return get_confirmation_message(state_manager, flow_type)

        else:
            error_context = ErrorContext(
                error_type="flow",
                message=f"Invalid {flow_type} step: {step}",
                step_id=step,
                details={
                    "flow_type": flow_type,
                    "input": input_data
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException(f"Invalid step: {step}"),
                state_manager,
                error_context
            ))

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=f"Failed to process {flow_type} step. Please try again",
            step_id=step,
            details={
                "flow_type": flow_type,
                "input": input_data,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


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
