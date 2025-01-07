"""Flow management with clean architecture patterns

This module provides flow management using:
- Pure UI validation in components
- State tracking with clear boundaries
- Proper validation state management
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from core.components import create_component
from core.utils.error_types import ValidationResult
from core.utils.exceptions import FlowException

from .registry import FlowRegistry


class FlowManager:
    """Manages flow progression and component state"""

    def __init__(self, flow_type: str, state_manager: Any):
        """Initialize flow manager"""
        self.flow_type = flow_type
        self.state_manager = state_manager
        self.config = FlowRegistry.get_flow_config(flow_type)
        self.components = {}

    def get_component(self, step: str, component_type: str = None) -> Any:
        """Get component for step with validation

        Args:
            step: Step identifier
            component_type: Optional specific component type to get.
                          If not provided, gets component types from registry.
        """
        # Validate step
        FlowRegistry.validate_flow_step(self.flow_type, step)

        # Get component type if not provided
        if not component_type:
            registry_type = FlowRegistry.get_step_component(self.flow_type, step)
            if isinstance(registry_type, list):
                component_type = registry_type[0]
            else:
                component_type = registry_type

        # Get/create component using cache key
        cache_key = f"{step}_{component_type}"
        if cache_key not in self.components:
            self.components[cache_key] = create_component(component_type)

        return self.components[cache_key]

    def process_step(self, step: str, value: Any) -> Tuple[ValidationResult, Optional[str]]:
        """Process step input with pure validation

        Args:
            step: Current step ID
            value: Input value

        Returns:
            Tuple of (ValidationResult, Optional[str]) where the string is an exit condition
            if the step produced one (e.g. from API response)

        Raises:
            FlowException: If step invalid
        """
        # Get component types for step
        component_types = FlowRegistry.get_step_component(self.flow_type, step)
        if not isinstance(component_types, list):
            component_types = [component_types]

        # Get current component state from state manager
        flow_state = self.state_manager.get_flow_state()
        if not flow_state:
            raise FlowException(
                message="No active flow state",
                step=step,
                action="process",
                data={}
            )

        component_state = flow_state.get("active_component", {})
        current_index = component_state.get("component_index", 0)

        # Get current component type
        if current_index >= len(component_types):
            raise FlowException(
                message=f"Invalid component index {current_index} for step {step}",
                step=step,
                action="process",
                data={"component_index": current_index}
            )

        current_type = component_types[current_index]

        # Get and validate current component
        component = self.get_component(step, current_type)
        validation = component.validate(value)

        # Check for exit condition in validation result
        exit_condition = None
        if validation.valid and hasattr(validation, "metadata"):
            exit_condition = validation.metadata.get("exit_condition")

        return validation, exit_condition


def initialize_flow(
    state_manager: Any,
    flow_type: str,
    step: Optional[str] = None,
    initial_data: Optional[Dict] = None
) -> None:
    """Initialize flow state with proper structure

    Args:
        state_manager: State manager instance
        flow_type: Type of flow
        step: Optional starting step (defaults to first step)
        initial_data: Optional initial business data

    Raises:
        FlowException: If flow type invalid
    """
    # Get flow config
    config = FlowRegistry.get_flow_config(flow_type)
    steps = config["steps"]

    # Get initial step and index
    if not step:
        step = steps[0]
        step_index = 0
    else:
        FlowRegistry.validate_flow_step(flow_type, step)
        try:
            step_index = steps.index(step)
        except ValueError:
            raise FlowException(
                message=f"Invalid step {step} for flow {flow_type}",
                step=step,
                action="initialize",
                data={"flow_type": flow_type}
            )

    # Get component type(s) for step
    component_types = FlowRegistry.get_step_component(flow_type, step)
    if not isinstance(component_types, list):
        component_types = [component_types]

    # Use first component for initial state
    initial_component = component_types[0]

    # Check if step should auto-progress
    should_auto_progress = FlowRegistry.should_auto_progress(flow_type, step)

    # Create flow state with standardized validation tracking
    validation_state = {
        "in_progress": True,
        "attempts": 0,
        "last_attempt": None,
        "operation": "initialize_flow",
        "component": initial_component,
        "components": component_types,  # Store all components
        "auto_progress": should_auto_progress,  # Track auto-progress status
        "timestamp": datetime.utcnow().isoformat()
    }

    flow_state = {
        "flow_data": {
            # Flow identification with validation
            "flow_type": flow_type,
            "handler_type": config.get("handler_type", "member"),
            "step": step,
            "step_index": step_index,
            "total_steps": len(steps),
            "validation": validation_state,

            # Component state with tracking
            "active_component": {
                "type": initial_component,
                "components": component_types,  # Store all components
                "component_index": 0,  # Track current component
                "value": None,
                "auto_progress": should_auto_progress,  # Track auto-progress status
                "validation": {
                    "in_progress": False,
                    "error": None,
                    "attempts": 0,
                    "last_attempt": None,
                    "operation": "initialize_component",
                    "component": initial_component,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },

            # Business data with timestamp
            "data": {
                **(initial_data or {}),
                "_metadata": {
                    "initialized_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        }
    }

    # Update only flow state, preserving other state
    state_manager.update_state({
        "flow_data": flow_state["flow_data"]  # Only update flow_data portion
    })


def process_flow_input(
    state_manager: Any,
    input_data: Any
) -> Optional[Dict]:
    """Process flow input with validation

    Args:
        state_manager: State manager instance
        input_data: Input value

    Returns:
        None if complete, or dict with next step/flow info

    Raises:
        FlowException: If flow state invalid
    """
    # Get flow state
    flow_data = state_manager.get_flow_state()
    if not flow_data:
        raise FlowException(
            message="No active flow",
            step="unknown",
            action="process",
            data={}
        )

    flow_type = flow_data["flow_type"]
    current_step = flow_data["step"]
    current_index = flow_data["step_index"]
    total_steps = flow_data["total_steps"]

    # Get handler type
    handler_type = flow_data.get("handler_type", "member")

    # Process through flow manager
    flow_manager = FlowManager(flow_type, state_manager)
    validation, exit_condition = flow_manager.process_step(current_step, input_data)

    # Update validation state with tracking
    component_state = flow_data["active_component"]
    validation_state = {
        "in_progress": True,
        "attempts": component_state["validation"]["attempts"] + 1,
        "last_attempt": {
            "value": input_data,
            "timestamp": datetime.utcnow().isoformat()
        },
        "operation": "validate_input",
        "component": component_state["type"],
        "timestamp": datetime.utcnow().isoformat()
    }

    # Handle validation error with tracking
    if not validation.valid:
        validation_state.update({
            "in_progress": False,
            "error": {
                "message": validation.error.get("message"),
                "details": validation.error.get("details", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        state_manager.update_state({
            "flow_data": {
                "active_component": {
                    **component_state,
                    "validation": validation_state
                }
            }
        })
        return {
            "error": validation.error,
            "validation": validation_state
        }

    # Update component state with valid value and tracking
    validation_state.update({
        "in_progress": False,
        "error": None,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Get current components array and index
    components = component_state.get("components", [])
    component_index = component_state.get("component_index", 0)

    # Update state preserving component tracking
    state_manager.update_state({
        "flow_data": {
            "active_component": {
                **component_state,
                "value": validation.value,
                "validation": validation_state,
                "components": components,  # Preserve components array
                "component_index": component_index,  # Preserve current index
                "updated_at": datetime.utcnow().isoformat()
            }
        }
    })

    # Check for exit condition
    if exit_condition:
        next_flow = FlowRegistry.get_exit_flow(flow_type, exit_condition)
        if next_flow:
            # Clear current flow state
            complete_flow(state_manager)
            # Initialize next flow
            initialize_flow(state_manager, next_flow)
            return {
                "flow_transition": {
                    "from": flow_type,
                    "to": next_flow,
                    "condition": exit_condition
                }
            }
        elif exit_condition == "error":
            # Stay in current flow on error
            return {
                "error": {
                    "message": "Operation failed",
                    "details": validation.metadata.get("error_details", {})
                }
            }

    # Get next step
    next_step = FlowRegistry.get_next_step(flow_type, current_step)
    if next_step == "complete":
        # Check for success exit condition
        next_flow = FlowRegistry.get_exit_flow(flow_type, "success")
        if next_flow:
            # Clear current flow state
            complete_flow(state_manager)
            # Initialize next flow
            initialize_flow(state_manager, next_flow)
            return {
                "flow_transition": {
                    "from": flow_type,
                    "to": next_flow,
                    "condition": "success"
                }
            }
        return None

    # Get next component type(s)
    next_component_types = FlowRegistry.get_step_component(flow_type, next_step)
    if not isinstance(next_component_types, list):
        next_component_types = [next_component_types]

    # Use first component for initial state
    initial_component = next_component_types[0]

    # Check if next step should auto-progress
    should_auto_progress = FlowRegistry.should_auto_progress(flow_type, next_step)

    # Create next component validation state
    next_validation_state = {
        "in_progress": False,
        "error": None,
        "attempts": 0,
        "last_attempt": None,
        "operation": "initialize_component",
        "component": initial_component,
        "auto_progress": should_auto_progress,  # Track auto-progress status
        "timestamp": datetime.utcnow().isoformat()
    }

    # Update step and component state with tracking
    state_manager.update_state({
        "flow_data": {
            "step": next_step,
            "step_index": current_index + 1,
            "active_component": {
                "type": initial_component,
                "components": next_component_types,  # Store all components
                "component_index": 0,  # Reset index for new step
                "value": None,
                "auto_progress": should_auto_progress,  # Track auto-progress status
                "validation": next_validation_state,
                "created_at": datetime.utcnow().isoformat()
            },
            "updated_at": datetime.utcnow().isoformat()
        }
    })

    return {
        "step": next_step,
        "handler_type": handler_type,
        "auto_progress": should_auto_progress,  # Include auto-progress status in response
        "progress": {
            "current": current_index + 1,
            "total": total_steps
        }
    }


def complete_flow(state_manager: Any) -> None:
    """Complete flow and clear state

    Args:
        state_manager: State manager instance
    """
    state_manager.update_state({
        "flow_data": None
    })
