"""Core state utilities enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

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
    # Get current state
    current_state = state_manager._state.copy()

    # Handle state updates without transformation
    for key, value in updates.items():
        if key == "flow_data" and isinstance(value, dict):
            # Special handling for flow_data to preserve structure
            current_flow_data = current_state.get("flow_data", {})
            if isinstance(current_flow_data, dict):
                # Deep merge flow_data to preserve all fields
                new_flow_data = current_flow_data.copy()
                for k, v in value.items():
                    if k == "data" and isinstance(v, dict):
                        # Merge data dictionary
                        current_data = new_flow_data.get("data", {})
                        if isinstance(current_data, dict):
                            new_flow_data["data"] = {**current_data, **v}
                        else:
                            new_flow_data["data"] = v
                    else:
                        # Update other fields
                        new_flow_data[k] = v
                current_state["flow_data"] = new_flow_data
            else:
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

    # Update internal state on success
    if success:
        state_manager._state = current_state

    return success, error


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


def update_flow_data(state_manager: Any, data_updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Update flow data structure while preserving flow state

    Args:
        state_manager: State manager instance
        data_updates: Dictionary of data updates

    Returns:
        Tuple of (success, error_message)
    """
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
