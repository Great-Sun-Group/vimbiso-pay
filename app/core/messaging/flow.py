"""Flow management with clean architecture patterns

This module provides flow management using:
- Pure UI validation in components
- State tracking with clear boundaries
- Proper validation state management
"""

from typing import Any, Dict, Optional

from core.components import create_component
from core.utils.exceptions import FlowException
from core.utils.error_types import ValidationResult
from .registry import FlowRegistry


class FlowManager:
    """Manages flow progression and component state"""

    def __init__(self, flow_type: str):
        """Initialize flow manager"""
        self.flow_type = flow_type
        self.config = FlowRegistry.get_flow_config(flow_type)
        self.components = {}

    def get_component(self, step: str) -> Any:
        """Get component for step with validation"""
        # Validate step
        FlowRegistry.validate_flow_step(self.flow_type, step)

        # Get/create component
        if step not in self.components:
            component_type = FlowRegistry.get_step_component(self.flow_type, step)
            self.components[step] = create_component(component_type)

        return self.components[step]

    def process_step(self, step: str, value: Any) -> ValidationResult:
        """Process step input with pure validation

        Args:
            step: Current step ID
            value: Input value

        Returns:
            ValidationResult with validation status

        Raises:
            FlowException: If step invalid
        """
        # Get component
        component = self.get_component(step)

        # Only handle UI validation
        return component.validate(value)


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

    # Get component type for step
    component_type = FlowRegistry.get_step_component(flow_type, step)

    # Create flow state with proper structure
    flow_state = {
        "flow_data": {
            # Flow identification
            "flow_type": flow_type,
            "handler_type": config.get("handler_type", "member"),
            "step": step,
            "step_index": step_index,
            "total_steps": len(steps),

            # Component state
            "active_component": {
                "type": component_type,
                "value": None,
                "validation": {
                    "in_progress": False,
                    "error": None,
                    "attempts": 0,
                    "last_attempt": None
                }
            },

            # Business data
            "data": initial_data or {}
        }
    }

    # Update state
    state_manager.update_state(flow_state)


def process_flow_input(
    state_manager: Any,
    input_data: Any
) -> Optional[Dict]:
    """Process flow input with validation

    Args:
        state_manager: State manager instance
        input_data: Input value

    Returns:
        None if complete, or dict with next step

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
    flow_manager = FlowManager(flow_type)
    validation = flow_manager.process_step(current_step, input_data)

    # Update validation state
    component_state = flow_data["active_component"]
    component_state["validation"]["attempts"] += 1
    component_state["validation"]["last_attempt"] = input_data

    # Handle validation error
    if not validation.valid:
        component_state["validation"]["error"] = validation.error
        component_state["validation"]["in_progress"] = False
        state_manager.update_state({
            "flow_data": {
                "active_component": component_state
            }
        })
        return {"error": validation.error}

    # Update component state with valid value
    component_state.update({
        "value": validation.value,
        "validation": {
            "in_progress": False,
            "error": None,
            "attempts": component_state["validation"]["attempts"],
            "last_attempt": input_data
        }
    })
    state_manager.update_state({
        "flow_data": {
            "active_component": component_state
        }
    })

    # Get next step
    next_step = FlowRegistry.get_next_step(flow_type, current_step)
    if next_step == "complete":
        return None

    # Get next component type
    next_component_type = FlowRegistry.get_step_component(flow_type, next_step)

    # Update step and component state
    state_manager.update_state({
        "flow_data": {
            "step": next_step,
            "step_index": current_index + 1,
            "active_component": {
                "type": next_component_type,
                "value": None,
                "validation": {
                    "in_progress": False,
                    "error": None,
                    "attempts": 0,
                    "last_attempt": None
                }
            }
        }
    })

    return {
        "step": next_step,
        "handler_type": handler_type,
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
