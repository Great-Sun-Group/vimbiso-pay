"""Core state utilities enforcing SINGLE SOURCE OF TRUTH

This module provides simplified state management with clear boundaries
and minimal nesting.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.utils.exceptions import (ComponentException, FlowException,
                                   SystemException)
from .interface import StateManagerInterface

logger = logging.getLogger(__name__)


def prepare_state_update(state_manager: StateManagerInterface, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare state update with validation tracking

    Args:
        state_manager: State manager instance
        updates: Dictionary of updates to apply

    Returns:
        Dict[str, Any]: Prepared state updates

    Raises:
        ComponentException: If updates format is invalid
    """
    # Get current state with validation tracking
    current_state = {}
    for key in ["flow_data", "update_attempts"]:
        value = state_manager.get(key)
        if value is not None:
            current_state[key] = value

    validation_state = {
        "in_progress": True,
        "attempts": current_state.get("update_attempts", 0) + 1,
        "last_attempt": datetime.utcnow().isoformat()
    }

    # Handle flow data updates with validation
    if "flow_data" in updates:
        flow_data = updates["flow_data"]
        if flow_data is None:
            # Clear flow state with validation
            current_state["flow_data"] = {
                "validation": {
                    **validation_state,
                    "in_progress": False,
                    "operation": "clear"
                }
            }
        elif isinstance(flow_data, dict):
            # Get current flow state
            current_flow = current_state.get("flow_data", {})

            # Update flow state with validation
            # Start with current flow data
            new_data = current_flow.get("data", {}) if current_flow else {}

            # Only update with new data if provided
            if flow_data and isinstance(flow_data.get("data"), dict):
                # Preserve selection data if present
                selection = new_data.get("selection")

                # Deep merge to preserve nested structure
                for key, value in flow_data["data"].items():
                    if isinstance(value, dict) and isinstance(new_data.get(key), dict):
                        # Merge nested dicts
                        new_data[key] = {**new_data[key], **value}
                    else:
                        # Replace or add non-dict values
                        new_data[key] = value

                # Restore selection data if it was present
                if selection:
                    new_data["selection"] = selection

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Merged flow data: {new_data}")

            current_state["flow_data"] = {
                "context": flow_data.get("context", current_flow.get("context")),
                "component": flow_data.get("component", current_flow.get("component")),
                "data": new_data,
                "awaiting_input": flow_data.get("awaiting_input", current_flow.get("awaiting_input", False))
            }

            # Only log context/component changes at INFO level
            if (flow_data.get("context") != current_flow.get("context") or
               flow_data.get("component") != current_flow.get("component")):
                logger.info(f"State transition: {current_flow.get('context')}.{current_flow.get('component')} -> {flow_data.get('context')}.{flow_data.get('component')}")
        else:
            validation_state.update({
                "in_progress": False,
                "error": "Invalid flow data format"
            })
            raise ComponentException(
                message="Invalid flow data format",
                component="state_utils",
                field="flow_data",
                value=str(type(flow_data)),
                validation=validation_state
            )

    # Handle other updates with validation
    for key, value in updates.items():
        if key != "flow_data":
            if isinstance(value, dict) and "validation" not in value:
                value["validation"] = {
                    **validation_state,
                    "in_progress": False,
                    "operation": f"update_{key}"
                }
            current_state[key] = value

    # Add validation tracking
    current_state["update_attempts"] = validation_state["attempts"]
    return current_state


def update_flow_state(
    state_manager: StateManagerInterface,
    context: str,
    component: str,
    data: Optional[Dict] = None
) -> None:
    """Update flow state with validation tracking

    Args:
        state_manager: State manager instance
        context: Current context
        component: Current component
        data: Optional flow data

    Raises:
        SystemException: If flow state update fails
    """
    try:
        # Get current flow state for validation
        current_flow = state_manager.get_flow_state() or {}

        # Create flow update with validation
        flow_data = {
            "context": context,
            "component": component,
            "data": data or {},
            "validation": {
                "in_progress": True,
                "attempts": current_flow.get("validation_attempts", 0) + 1,
                "last_attempt": datetime.utcnow().isoformat()
            }
        }

        # Prepare and apply state update
        prepared_state = prepare_state_update(state_manager, {
            "flow_data": flow_data
        })
        state_manager.update_state(prepared_state)

    except Exception as e:
        logger.error(f"Failed to update flow state {context}.{component}: {str(e)}")
        raise SystemException(
            message=f"Failed to update flow state: {str(e)}",
            code="FLOW_STATE_ERROR",
            service="state_utils",
            action="update_flow_state"
        )


def update_flow_data(
    state_manager: StateManagerInterface,
    data: Dict[str, Any]
) -> None:
    """Update flow data

    Args:
        state_manager: State manager instance
        data: Flow data updates

    Raises:
        FlowException: If no active flow
        SystemException: If flow data update fails
    """
    try:
        # Get current flow state
        flow_state = state_manager.get("flow_data")
        if not flow_state:
            raise FlowException(
                message="No active flow",
                step="update_data",
                action="validate_flow",
                data={"data_keys": list(data.keys())}
            )

        # Prepare and apply state update
        prepared_state = prepare_state_update(state_manager, {
            "flow_data": {
                "data": data
            }
        })
        state_manager.update_state(prepared_state)

    except Exception as e:
        logger.error(f"Failed to update flow data: {str(e)}")
        raise SystemException(
            message=f"Failed to update flow data: {str(e)}",
            code="FLOW_DATA_ERROR",
            service="state_utils",
            action="update_flow_data"
        )


def clear_flow_state(state_manager: StateManagerInterface) -> None:
    """Clear flow state

    Args:
        state_manager: State manager instance

    Raises:
        SystemException: If flow state clear fails
    """
    try:
        # Prepare and apply state update
        prepared_state = prepare_state_update(state_manager, {
            "flow_data": None
        })
        state_manager.update_state(prepared_state)

    except Exception as e:
        logger.error(f"Failed to clear flow state: {str(e)}")
        raise SystemException(
            message=f"Failed to clear flow state: {str(e)}",
            code="FLOW_CLEAR_ERROR",
            service="state_utils",
            action="clear_flow_state"
        )
