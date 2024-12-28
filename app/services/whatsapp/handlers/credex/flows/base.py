"""Core credex flow functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def process_flow_step(
    state_manager: Any,
    flow_id: str,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Dict[str, Any]:
    """Process a flow step enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        flow_id: Flow identifier
        step: Current step name
        input_data: Optional input data
        credex_service: Optional CredEx service instance

    Returns:
        Dict containing flow step data

    Raises:
        StateException: If state validation fails
    """
    try:
        # Let StateManager validate state
        state_manager.get("channel")  # Validates channel exists
        flow_data = state_manager.get("flow_data")  # Validates flow data exists

        # Let StateManager validate service through state update
        if credex_service:
            state_manager.update_state({
                "flow_data": {
                    "service": credex_service  # StateManager validates service structure
                }
            })

        # Log validation (using state_manager for channel id)
        audit.log_flow_event(
            flow_id,
            "state_validation",
            None,
            {"channel_id": state_manager.get("channel")["identifier"]},  # StateManager validates
            "success"
        )

        # Return step data for handler
        return {
            "flow_id": flow_id,
            "step": step,
            "flow_data": flow_data,
            "input_data": input_data,
            "credex_service": credex_service
        }

    except StateException as e:
        logger.error(f"Flow step processing error: {str(e)}")
        raise  # Let caller handle error
