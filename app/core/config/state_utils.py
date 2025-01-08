"""Core state utilities enforcing SINGLE SOURCE OF TRUTH

This module provides simplified state management with clear boundaries
and minimal nesting.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.utils.exceptions import (ComponentException, FlowException,
                                   SystemException)

from .config import ACTIVITY_TTL

logger = logging.getLogger(__name__)


def update_state_core(state_manager: Any, updates: Dict[str, Any]) -> None:
    """Update state with validation tracking

    Args:
        state_manager: State manager instance
        updates: Dictionary of updates to apply

    Raises:
        ComponentException: If updates format is invalid
        SystemException: If state update fails
    """
    try:
        # Get current state with validation tracking
        current_state = state_manager._state.copy()
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
                    # Deep merge to preserve nested structure
                    for key, value in flow_data["data"].items():
                        if isinstance(value, dict) and isinstance(new_data.get(key), dict):
                            # Merge nested dicts
                            new_data[key] = {**new_data[key], **value}
                        else:
                            # Replace or add non-dict values
                            new_data[key] = value

                logger.info(f"Merged flow data: {new_data}")

                current_state["flow_data"] = {
                    "context": flow_data.get("context", current_flow.get("context")),
                    "component": flow_data.get("component", current_flow.get("component")),
                    "data": new_data,
                    "validation": {
                        **validation_state,
                        "in_progress": False,
                        "operation": "update"
                    }
                }

                logger.info(f"Updated flow state: {current_state['flow_data']}")
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

        # Store state atomically with validation
        state_manager.atomic_state.atomic_update(
            state_manager.key_prefix,
            current_state,
            ACTIVITY_TTL
        )

        # Update internal state with validation
        current_state["update_attempts"] = validation_state["attempts"]
        state_manager._state = current_state

    except Exception as e:
        validation_state = {
            "in_progress": False,
            "error": str(e),
            "attempts": current_state.get("update_attempts", 0) + 1,
            "last_attempt": datetime.utcnow().isoformat()
        }
        logger.error(
            "State update error",
            extra={
                "error": str(e),
                "update_keys": list(updates.keys()),
                "validation": validation_state
            }
        )
        raise SystemException(
            message=f"Failed to update state: {str(e)}",
            code="STATE_UPDATE_ERROR",
            service="state_utils",
            action="update_state"
        )


def update_flow_state(
    state_manager: Any,
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

        # Update state with validation
        update_state_core(state_manager, {
            "flow_data": flow_data
        })

    except Exception as e:
        validation_state = {
            "in_progress": False,
            "error": str(e),
            "attempts": current_flow.get("validation_attempts", 0) + 1,
            "last_attempt": datetime.utcnow().isoformat()
        }
        logger.error(
            "Flow state update error",
            extra={
                "error": str(e),
                "context": context,
                "component": component,
                "validation": validation_state
            }
        )
        raise SystemException(
            message=f"Failed to update flow state: {str(e)}",
            code="FLOW_STATE_ERROR",
            service="state_utils",
            action="update_flow_state"
        )


def update_flow_data(
    state_manager: Any,
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

        # Update flow data
        update_state_core(state_manager, {
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
        raise SystemException(
            message=f"Failed to update flow data: {str(e)}",
            code="FLOW_DATA_ERROR",
            service="state_utils",
            action="update_flow_data"
        )


def clear_flow_state(state_manager: Any) -> None:
    """Clear flow state

    Args:
        state_manager: State manager instance

    Raises:
        SystemException: If flow state clear fails
    """
    try:
        update_state_core(state_manager, {
            "flow_data": None
        })

    except Exception as e:
        logger.error(
            "Clear flow state error",
            extra={"error": str(e)}
        )
        raise SystemException(
            message=f"Failed to clear flow state: {str(e)}",
            code="FLOW_CLEAR_ERROR",
            service="state_utils",
            action="clear_flow_state"
        )
