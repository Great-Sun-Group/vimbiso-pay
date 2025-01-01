"""Action flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
from services.credex.service import get_member_accounts

from ...member.dashboard import handle_dashboard_display
from .messages import (create_action_confirmation, create_list_message,
                       create_success_message)

logger = logging.getLogger(__name__)

# Valid action types
VALID_ACTIONS = {"cancel", "accept", "decline", "registration", "upgrade"}


def validate_action_input(input_type: str, value: str, action: str) -> Dict[str, Any]:
    """Validate action input based on type"""
    if input_type == "select":
        if not value.startswith(f"{action}_"):
            raise StateException("Invalid selection. Please select from the list")

        credex_id = value[len(action) + 1:]
        if not credex_id:
            raise StateException("Invalid selection. Please select from the list")

        return {"credex_id": credex_id}

    elif input_type == "confirm":
        if not value or value.get("type") != "interactive":
            raise StateException("Please use the confirmation buttons")

        interactive = value.get("interactive", {})
        if interactive.get("type") != "button_reply":
            raise StateException("Please use the confirmation buttons")

        button_id = interactive.get("button_reply", {}).get("id")
        if button_id not in ["confirm_action", "cancel_action"]:
            raise StateException("Invalid button selection")

        return {"confirmed": button_id == "confirm_action"}

    raise StateException(f"Invalid input type: {input_type}")


def update_action_state(state_manager: Any, step: str, data: Dict[str, Any], action: str) -> None:
    """Update action state with validation"""
    if action not in VALID_ACTIONS:
        raise StateException(f"Invalid action type: {action}")

    state_manager.update_state({
        "flow_data": {
            "step": {"select": 1, "confirm": 2}[step],
            "current_step": step,
            "action_type": action,
            "data": data
        }
    })


def process_action_step(state_manager: Any, step: str, action: str, input_data: Any = None) -> Dict[str, Any]:
    """Process action step with validation"""
    try:
        # Get channel ID through state manager
        state = state_manager.get("channel")
        channel_id = state["identifier"]

        # Initial prompt
        if not input_data:
            return create_list_message(channel_id, action)

        # Validate input and update state
        try:
            validated = validate_action_input(step, input_data, action)
            update_action_state(state_manager, step, validated, action)
        except StateException as e:
            error_context = ErrorContext(
                error_type="input",
                message=str(e),
                step_id=step,
                details={"input": input_data}
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        # Handle step progression
        if step == "select":
            return create_action_confirmation(
                channel_id,
                validated["credex_id"],
                action
            )

        elif step == "confirm" and validated["confirmed"]:
            # Submit action
            try:
                response = get_member_accounts(state_manager)
                handle_dashboard_display(
                    state_manager,
                    success_message=f"Successfully {action}ed offer"
                )
            except Exception as e:
                error_context = ErrorContext(
                    error_type="api",
                    message=f"Failed to {action} offer",
                    step_id=step,
                    details={"error": str(e)}
                )
                raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

            # Log success
            logger.info(
                f"Action {action} completed",
                extra={
                    "action": action,
                    "channel_id": channel_id,
                    "response": response
                }
            )
            return create_success_message(channel_id)

        # Re-confirm if not confirmed
        state = state_manager.get_flow_step_data()
        return create_action_confirmation(
            channel_id,
            state["credex_id"],
            action
        )

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


def process_cancel_step(state_manager: Any, step: str, input_data: Any = None) -> Dict[str, Any]:
    """Process cancel step"""
    return process_action_step(state_manager, step, "cancel", input_data)


def process_accept_step(state_manager: Any, step: str, input_data: Any = None) -> Dict[str, Any]:
    """Process accept step"""
    return process_action_step(state_manager, step, "accept", input_data)


def process_decline_step(state_manager: Any, step: str, input_data: Any = None) -> Dict[str, Any]:
    """Process decline step"""
    return process_action_step(state_manager, step, "decline", input_data)
