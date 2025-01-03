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
    step: Optional[str] = None
) -> None:
    """Initialize flow state with proper structure

    Args:
        state_manager: State manager instance
        flow_type: Type of flow
        step: Optional starting step (defaults to first step)

    Raises:
        FlowException: If flow type invalid
    """
    # Get flow config
    config = FlowRegistry.get_flow_config(flow_type)

    # Get initial step
    if not step:
        step = config["steps"][0]
    else:
        FlowRegistry.validate_flow_step(flow_type, step)

    # Get component type for step
    component_type = FlowRegistry.get_step_component(flow_type, step)

    # Create flow state with proper structure
    flow_state = {
        "flow_data": {
            # Flow identification
            "flow_type": flow_type,
            "handler_type": config.get("handler_type", "member"),
            "step": step,
            "step_index": 0,

            # Component state
            "active_component": {
                "type": component_type,
                "value": None,
                "validation": {
                    "in_progress": False,
                    "error": None
                }
            },

            # Business data
            "data": {}
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

    # Get handler type
    handler_type = flow_data.get("handler_type", "member")

    # Process through flow manager
    flow_manager = FlowManager(flow_type)
    validation = flow_manager.process_step(current_step, input_data)

    # Handle validation error
    if not validation.valid:
        return {"error": validation.error}

    # Update component state
    state_manager.update_state({
        "flow_data": {
            "active_component": {
                "type": flow_data["active_component"]["type"],
                "value": validation.value,
                "validation": {
                    "in_progress": False,
                    "error": None
                }
            }
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
            "active_component": {
                "type": next_component_type,
                "value": None,
                "validation": {
                    "in_progress": False,
                    "error": None
                }
            }
        }
    })

    return {
        "step": next_step,
        "handler_type": handler_type
    }


def complete_flow(state_manager: Any) -> None:
    """Complete flow and clear state

    Args:
        state_manager: State manager instance
    """
    state_manager.update_state({
        "flow_data": None
    })
