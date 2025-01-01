"""Base flow functionality enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict


def initialize_flow_state(
    state_manager: Any,
    step: int,
    current_step: str,
    flow_type: str,
    credex_service: Any = None
) -> Dict[str, Any]:
    """Initialize flow state through validation"""
    # Let StateManager validate flow initialization
    state_manager.update_state({
        "validation": {
            "type": "flow_init",
            "data": {
                "step": step,
                "current_step": current_step,
                "flow_type": flow_type
            }
        }
    })

    # Let StateManager validate service if provided
    if credex_service:
        state_manager.update_state({
            "validation": {
                "type": "service_validation",
                "service_type": "credex",
                "service": credex_service
            }
        })

    # Let StateManager validate channel
    state_manager.update_state({
        "validation": {
            "type": "channel",
            "required": True
        }
    })

    # Get validated data
    flow_state = state_manager.get_flow_state()
    channel_id = state_manager.get_channel_id()
    service_data = state_manager.get_service_data() if credex_service else None

    # Return validated state
    state = {
        "step": flow_state["step"],
        "channel_id": channel_id,
        "flow_type": flow_state["flow_type"],
        "current_step": flow_state["current_step"]
    }

    if service_data:
        state["service"] = service_data

    return state
