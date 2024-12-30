"""Core credex flow functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)


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
        # Validate required state through single update
        state_update = {
            "flow_data": {
                "step_validation": {
                    "flow_id": flow_id,
                    "current_step": step
                }
            }
        }

        # Add service if provided
        if credex_service:
            state_update["flow_data"]["service"] = credex_service

        # Let StateManager validate all required fields
        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to validate flow state: {error}")

        # Get validated state data
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Invalid channel state")

        flow_data = state_manager.get("flow_data")
        if not flow_data:
            raise StateException("Missing flow data")

        # Log validation success
        logger.info(
            "Flow step validation successful",
            extra={
                "flow_id": flow_id,
                "step": step,
                "channel_id": channel["identifier"]
            }
        )

        # Return validated step data
        return {
            "flow_id": flow_id,
            "step": step,
            "flow_data": flow_data,
            "input_data": input_data,
            "credex_service": credex_service
        }

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id=step,
            details={
                "flow_id": flow_id,
                "operation": "process_flow_step",
                "has_input": bool(input_data),
                "has_service": bool(credex_service)
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise StateException(f"Flow step processing failed: {str(e)}")
