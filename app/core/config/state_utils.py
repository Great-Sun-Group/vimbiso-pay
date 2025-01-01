"""Core state utilities enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException

from .config import ACTIVITY_TTL, atomic_state

logger = logging.getLogger(__name__)


def _update_state_core(state_manager: Any, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Core state update function that provides atomic state structure updates

    Args:
        state_manager: State manager instance
        updates: Dictionary of updates to apply

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get current state
        current_state = state_manager._state.copy()

        # Handle state updates without transformation
        for key, value in updates.items():
            if key == "flow_data" and isinstance(value, dict):
                # Special handling for flow_data to preserve structure
                current_flow_data = current_state.get("flow_data", {})
                if isinstance(current_flow_data, dict):
                    # Start with new values
                    new_flow_data = value.copy()

                    # Preserve data if not in update
                    if "data" not in new_flow_data and "data" in current_flow_data:
                        new_flow_data["data"] = current_flow_data["data"]
                    # Merge data if both exist
                    elif "data" in new_flow_data and "data" in current_flow_data:
                        if isinstance(new_flow_data["data"], dict) and isinstance(current_flow_data["data"], dict):
                            new_flow_data["data"] = {**current_flow_data["data"], **new_flow_data["data"]}

                    # Ensure essential fields exist
                    new_flow_data.setdefault("flow_type", current_flow_data.get("flow_type"))
                    new_flow_data.setdefault("step", current_flow_data.get("step", 0))
                    new_flow_data.setdefault("current_step", current_flow_data.get("current_step", ""))

                    current_state["flow_data"] = new_flow_data
                else:
                    # If no existing flow_data, just use new value
                    current_state["flow_data"] = value
            elif isinstance(value, dict) and isinstance(current_state.get(key), dict):
                # For other dictionary fields, update nested values
                current_state[key].update(value)
            else:
                # For non-dictionary fields or new fields, set directly
                current_state[key] = value

        # Store state atomically
        success, error = atomic_state.atomic_update(
            state_manager.key_prefix,
            current_state,
            ACTIVITY_TTL
        )

        if not success:
            raise StateException(f"Failed to update state: {error}")

        # Update internal state on success
        state_manager._state = current_state
        return True, None

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "update_state_core",
                "update_keys": list(updates.keys())
            }
        )
        logger.error(
            "State update error",
            extra={
                "error": str(e),
                "error_context": error_context.__dict__
            }
        )
        raise StateException(f"Failed to update state: {str(e)}") from e


def update_flow_state(state_manager: Any, flow_type: str, step: int, current_step: str) -> Tuple[bool, Optional[str]]:
    """Update flow state structure while preserving data

    Args:
        state_manager: State manager instance
        flow_type: Type of flow (e.g. "offer", "auth")
        step: Integer step number for progression tracking
        current_step: String step identifier for routing

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}

        # Create complete flow update
        new_flow_data = {
            "flow_type": flow_type,
            "step": step,
            "current_step": current_step,
            "data": flow_data.get("data", {})
        }

        # Update state atomically
        return _update_state_core(state_manager, {
            "flow_data": new_flow_data
        })

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "update_flow_state",
                "flow_type": flow_type,
                "step": step,
                "current_step": current_step
            }
        )
        logger.error(
            "Flow state update error",
            extra={
                "error": str(e),
                "error_context": error_context.__dict__
            }
        )
        raise StateException(f"Failed to update flow state: {str(e)}") from e


def update_flow_data(state_manager: Any, data_updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Update flow data structure while preserving flow state

    Args:
        state_manager: State manager instance
        data_updates: Dictionary of data updates

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}

        # Create complete flow update preserving current state
        new_flow_data = {
            "flow_type": flow_data.get("flow_type"),
            "step": flow_data.get("step", 0),
            "current_step": flow_data.get("current_step", ""),
            "data": {
                **(flow_data.get("data", {})),
                **data_updates
            }
        }

        # Update state atomically
        return _update_state_core(state_manager, {
            "flow_data": new_flow_data
        })

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "update_flow_data",
                "data_keys": list(data_updates.keys())
            }
        )
        logger.error(
            "Flow data update error",
            extra={
                "error": str(e),
                "error_context": error_context.__dict__
            }
        )
        raise StateException(f"Failed to update flow data: {str(e)}") from e


def advance_flow(
    state_manager: Any,
    next_step: str,
    data_updates: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """Advance flow structure to next step while optionally updating data

    Args:
        state_manager: State manager instance
        next_step: String identifier of next step
        data_updates: Optional dictionary of data updates

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}

        # Create complete flow update
        new_flow_data = {
            "flow_type": flow_data.get("flow_type"),
            "step": flow_data.get("step", 0) + 1,
            "current_step": next_step,
            "data": {
                **(flow_data.get("data", {})),
                **(data_updates or {})
            }
        }

        # Update state atomically
        return _update_state_core(state_manager, {
            "flow_data": new_flow_data
        })

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "advance_flow",
                "next_step": next_step,
                "has_updates": bool(data_updates)
            }
        )
        logger.error(
            "Flow advance error",
            extra={
                "error": str(e),
                "error_context": error_context.__dict__
            }
        )
        raise StateException(f"Failed to advance flow: {str(e)}") from e
