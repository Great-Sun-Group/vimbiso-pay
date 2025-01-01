"""Core credex flow functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)


def validate_flow_state(state_manager: Any, flow_id: str, step: str) -> None:
    """Validate flow state through state manager"""
    state_manager.update_state({
        "flow_data": {
            "step": 0,  # Base validation always starts at 0
            "current_step": step,
            "flow_id": flow_id,
            "validation": {
                "required_fields": {
                    "channel": True,
                    "flow_data": True
                }
            }
        }
    })


def process_flow_step(
    state_manager: Any,
    flow_id: str,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Dict[str, Any]:
    """Process a flow step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate flow state through state manager
        validate_flow_state(state_manager, flow_id, step)

        # Update state with service if provided
        if credex_service:
            state_manager.update_state({
                "flow_data": {
                    "service": credex_service
                }
            })

        # Get validated state
        flow_data = state_manager.get_flow_step_data()

        # Log validation success
        logger.info(
            "Flow step validation successful",
            extra={
                "flow_id": flow_id,
                "step": step,
                "channel_id": state_manager.get("channel")["identifier"]
            }
        )

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
            message="Failed to process flow step",
            step_id=step,
            details={
                "flow_id": flow_id,
                "has_input": bool(input_data),
                "has_service": bool(credex_service),
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
