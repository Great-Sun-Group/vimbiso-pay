"""Flow management with component coordination

This module provides flow management using the component system.
Flows coordinate components and manage progression through steps.
"""

from typing import Any, Dict, Optional

from core.components import create_component
from core.utils.exceptions import FlowException
from .registry import FlowRegistry


class FlowManager:
    """Manages flow progression and components"""

    def __init__(self, flow_type: str):
        """Initialize flow manager"""
        self.flow_type = flow_type
        self.config = FlowRegistry.get_flow_config(flow_type)
        self.components = {}

    def get_component(self, step: str) -> Any:
        """Get component for step"""
        # Validate step
        FlowRegistry.validate_flow_step(self.flow_type, step)

        # Get/create component
        if step not in self.components:
            component_type = FlowRegistry.get_step_component(self.flow_type, step)
            self.components[step] = create_component(component_type)

        return self.components[step]

    def process_step(self, step: str, value: Any) -> Dict:
        """Process step input

        Args:
            step: Current step ID
            value: Input value

        Returns:
            On success: Verified data dict
            On error: Error dict

        Raises:
            FlowException: If step invalid
        """
        # Get component
        component = self.get_component(step)

        # Validate input
        result = component.validate(value)
        if "error" in result:
            return result

        # Convert to verified data
        return component.to_verified_data(value)


def initialize_flow(
    state_manager: Any,
    flow_type: str,
    step: Optional[str] = None
) -> None:
    """Initialize or update flow state

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

    # Create flow state with handler type
    flow_state = {
        "flow_data": {
            "flow_type": flow_type,
            "handler_type": config.get("handler_type", "member"),
            "step": step,
            "data": {}
        }
    }

    # Update state
    state_manager.update_state(flow_state)


def process_flow_input(
    state_manager: Any,
    input_data: Any
) -> Optional[Dict]:
    """Process flow input

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

    # Process step through appropriate handler
    flow_manager = FlowManager(flow_type)
    result = flow_manager.process_step(current_step, input_data)

    # Include handler type in result for routing
    if isinstance(result, dict) and "error" not in result:
        result["handler_type"] = handler_type

    # Handle error
    if "error" in result:
        return result

    # Update state with verified data
    state_manager.update_state({
        "flow_data": {
            "data": {
                current_step: result
            }
        }
    })

    # Get next step
    next_step = FlowRegistry.get_next_step(flow_type, current_step)
    if next_step == "complete":
        return None

    # Update step
    state_manager.update_state({
        "flow_data": {
            "step": next_step
        }
    })

    return {"step": next_step}


def complete_flow(state_manager: Any) -> None:
    """Complete flow and clear state

    Args:
        state_manager: State manager instance
    """
    state_manager.update_state({
        "flow_data": None
    })
