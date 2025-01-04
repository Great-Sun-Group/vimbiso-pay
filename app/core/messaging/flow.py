"""Flow management with clean architecture patterns

This module provides flow management using:
- Pure UI validation in components
- State tracking with clear boundaries
- Proper validation state management
"""

from datetime import datetime
from typing import Any, Dict, Optional

from core.components import create_component
from core.utils.error_types import ValidationResult
from core.utils.exceptions import FlowException

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

    # Create flow state with standardized validation tracking
    validation_state = {
        "in_progress": True,
        "attempts": 0,
        "last_attempt": None,
        "operation": "initialize_flow",
        "component": component_type,
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
                "type": component_type,
                "value": None,
                "validation": {
                    "in_progress": False,
                    "error": None,
                    "attempts": 0,
                    "last_attempt": None,
                    "operation": "initialize_component",
                    "component": component_type,
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

    component_state.update({
        "value": validation.value,
        "validation": validation_state,
        "updated_at": datetime.utcnow().isoformat()
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

    # Create next component validation state
    next_validation_state = {
        "in_progress": False,
        "error": None,
        "attempts": 0,
        "last_attempt": None,
        "operation": "initialize_component",
        "component": next_component_type,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Update step and component state with tracking
    state_manager.update_state({
        "flow_data": {
            "step": next_step,
            "step_index": current_index + 1,
            "active_component": {
                "type": next_component_type,
                "value": None,
                "validation": next_validation_state,
                "created_at": datetime.utcnow().isoformat()
            },
            "updated_at": datetime.utcnow().isoformat()
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
