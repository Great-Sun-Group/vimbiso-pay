"""Flow step processing with state validation through StateManager"""
from typing import Any, Dict, Optional


def process_step(state_manager: Any, step: str, input_data: Optional[Any] = None, action: Optional[str] = None) -> Dict[str, Any]:
    """Process flow step input with validation through state updates

    Args:
        state_manager: Manages state validation and updates
        step: Current step name
        input_data: Step input to validate
        action: Optional action type for action flows

    Returns:
        Validated step data
    """
    # Skip empty input - let flow handle initial prompts
    if not input_data:
        return {}

    # Let StateManager validate step input
    state_manager.update_state({
        "validation": {
            "type": "step_input",
            "step": step,
            "input": input_data,
            "action": action
        }
    })

    # Get validated step data
    step_data = state_manager.get_step_data()

    # Let StateManager validate step state
    state_manager.update_state({
        "validation": {
            "type": "step_state",
            "step": step,
            "data": step_data,
            "action": action
        }
    })

    # Return validated step data
    return state_manager.get_step_data()
