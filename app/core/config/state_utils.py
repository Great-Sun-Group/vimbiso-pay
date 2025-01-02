"""Core state utilities enforcing SINGLE SOURCE OF TRUTH

This module provides simplified state management with clear boundaries
and minimal nesting.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException
from .config import ACTIVITY_TTL

logger = logging.getLogger(__name__)


def update_state_core(state_manager: Any, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Update state with validation

    Args:
        state_manager: State manager instance
        updates: Dictionary of updates to apply

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get current state
        current_state = state_manager._state.copy()

        # Handle flow data updates
        if "flow_data" in updates:
            flow_data = updates["flow_data"]
            if flow_data is None:
                # Clear flow state
                current_state["flow_data"] = None
            elif isinstance(flow_data, dict):
                # Update flow state
                current_state["flow_data"] = {
                    "flow_type": flow_data.get("flow_type", current_state.get("flow_data", {}).get("flow_type")),
                    "step": flow_data.get("step", current_state.get("flow_data", {}).get("step")),
                    "data": {
                        **(current_state.get("flow_data", {}).get("data", {})),
                        **(flow_data.get("data", {}))
                    }
                }
            else:
                raise StateException("flow_data must be dict or None")

        # Handle other updates
        for key, value in updates.items():
            if key != "flow_data":
                current_state[key] = value

        # Store state atomically
        success, error = state_manager.atomic_state.atomic_update(
            state_manager.key_prefix,
            current_state,
            ACTIVITY_TTL
        )

        if not success:
            raise StateException(f"Failed to update state: {error}")

        # Update internal state
        state_manager._state = current_state
        return True, None

    except Exception as e:
        logger.error(
            "State update error",
            extra={
                "error": str(e),
                "update_keys": list(updates.keys())
            }
        )
        return False, str(e)


def update_flow_state(
    state_manager: Any,
    flow_type: str,
    step: str,
    data: Optional[Dict] = None
) -> Tuple[bool, Optional[str]]:
    """Update flow state

    Args:
        state_manager: State manager instance
        flow_type: Type of flow
        step: Current step
        data: Optional flow data

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Create flow update
        flow_data = {
            "flow_type": flow_type,
            "step": step,
            "data": data or {}
        }

        # Update state
        return update_state_core(state_manager, {
            "flow_data": flow_data
        })

    except Exception as e:
        logger.error(
            "Flow state update error",
            extra={
                "error": str(e),
                "flow_type": flow_type,
                "step": step
            }
        )
        return False, str(e)


def update_flow_data(
    state_manager: Any,
    data: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Update flow data

    Args:
        state_manager: State manager instance
        data: Flow data updates

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get current flow state
        flow_state = state_manager.get("flow_data")
        if not flow_state:
            raise StateException("No active flow")

        # Update flow data
        return update_state_core(state_manager, {
            "flow_data": {
                "data": data
            }
        })

    except Exception as e:
        logger.error(
            "Flow data update error",
            extra={
                "error": str(e),
                "data_keys": list(data.keys())
            }
        )
        return False, str(e)


def clear_flow_state(state_manager: Any) -> Tuple[bool, Optional[str]]:
    """Clear flow state

    Args:
        state_manager: State manager instance

    Returns:
        Tuple of (success, error_message)
    """
    try:
        return update_state_core(state_manager, {
            "flow_data": None
        })

    except Exception as e:
        logger.error(
            "Clear flow state error",
            extra={"error": str(e)}
        )
        return False, str(e)
