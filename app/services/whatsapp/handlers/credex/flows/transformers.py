"""Data transformation logic for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Union

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
logger = logging.getLogger(__name__)


def transform_button_input(input_data: Union[str, Dict[str, Any]], state_manager: Any) -> Optional[str]:
    """Transform button input to standardized format

    Args:
        input_data: Raw button input
        state_manager: State manager instance

    Returns:
        Button ID string or None if invalid

    Raises:
        StateException: If validation fails
    """
    try:
        # Extract button ID from interactive or text
        if isinstance(input_data, dict):
            interactive = input_data.get("interactive", {})
            if interactive.get("type") == "button_reply":
                return interactive.get("button_reply", {}).get("id")

        # Handle direct button ID string
        elif isinstance(input_data, str):
            return input_data.strip()

        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}
        current_step = flow_data.get("current_step", "confirm")

        error_context = ErrorContext(
            error_type="flow",
            message="Invalid button selection",
            step_id=current_step,
            details={
                "input": input_data,
                "flow_type": "offer",
                "validation_type": "button",
                "flow_data": flow_data
            }
        )
        raise StateException(ErrorHandler.handle_error(
            StateException("Invalid button input"),
            state_manager,
            error_context
        ))

    except Exception as e:
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}
        current_step = flow_data.get("current_step", "confirm")

        error_context = ErrorContext(
            error_type="flow",
            message="Invalid button selection",
            step_id=current_step,
            details={
                "input": input_data,
                "error": str(e),
                "flow_type": "offer",
                "validation_type": "button",
                "flow_data": flow_data
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def transform_handle(handle: Union[str, Dict[str, Any]], state_manager: Any) -> str:
    """Transform handle input to standardized format

    Args:
        handle: Raw handle input
        state_manager: State manager instance

    Returns:
        Validated handle string

    Raises:
        StateException: If validation fails
    """
    try:
        # Extract handle from interactive or text
        if isinstance(handle, dict):
            interactive = handle.get("interactive", {})
            if interactive.get("type") == "text":
                handle = interactive.get("text", {}).get("body", "")
            else:
                # Get current flow data
                flow_data = state_manager.get("flow_data") or {}
                current_step = flow_data.get("current_step", "handle")

                error_context = ErrorContext(
                    error_type="flow",
                    message="Invalid handle format. Please provide a valid account handle",
                    step_id=current_step,
                    details={
                        "input": handle,
                        "flow_type": "offer",
                        "validation_type": "handle_format",
                        "flow_data": flow_data
                    }
                )
                raise StateException(ErrorHandler.handle_error(
                    StateException("Invalid handle format"),
                    state_manager,
                    error_context
                ))

        handle = handle.strip()
        if not handle:
            # Get current flow data
            flow_data = state_manager.get("flow_data") or {}
            current_step = flow_data.get("current_step", "handle")

            error_context = ErrorContext(
                error_type="flow",
                message="Handle cannot be empty. Please provide a valid account handle",
                step_id=current_step,
                details={
                    "input": handle,
                    "flow_type": "offer",
                    "validation_type": "handle_empty",
                    "flow_data": flow_data
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException("Empty handle"),
                state_manager,
                error_context
            ))

        return handle

    except Exception as e:
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}
        current_step = flow_data.get("current_step", "handle")

        error_context = ErrorContext(
            error_type="flow",
            message="Invalid account handle. Please provide a valid handle",
            step_id=current_step,
            details={
                "input": handle,
                "error": str(e),
                "flow_type": "offer",
                "validation_type": "handle",
                "flow_data": flow_data
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def store_dashboard_data(state_manager: Any, response: Dict[str, Any]) -> None:
    """Store dashboard data enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        response: API response data

    Raises:
        StateException: If validation or storage fails
    """
    try:
        timestamp = datetime.utcnow().isoformat()

        # Let StateManager validate response through state update
        state_manager.update_state({
            "flow_data": {
                "dashboard": {
                    "data": response.get("data", {}).get("dashboard", {}),
                    "last_updated": timestamp
                }
            }
        })

        # Let StateManager validate action data through state update
        action = response.get("data", {}).get("action", {})
        if action:
            state_manager.update_state({
                "flow_data": {
                    "data": {
                        "action_id": action.get("id"),
                        "action_type": action.get("type"),
                        "action_timestamp": timestamp,
                        "action_status": "success" if action.get("type") == "CREDEX_CREATED" else action.get("status", "")
                    }
                }
            })

        # Log success
        logger.info(f"Successfully stored dashboard data for channel {state_manager.get('channel')['identifier']}")

    except Exception as e:
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}
        current_step = flow_data.get("current_step", "complete")

        error_context = ErrorContext(
            error_type="flow",
            message="Failed to store dashboard data. Please try again",
            step_id=current_step,
            details={
                "response": response,
                "error": str(e),
                "flow_type": "offer",
                "validation_type": "dashboard",
                "flow_data": flow_data
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
