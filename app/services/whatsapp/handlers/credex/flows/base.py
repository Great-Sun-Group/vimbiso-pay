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
        # Let StateManager validate state
        try:
            state_manager.get("channel")  # Validates channel exists
        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Channel information not found. Please restart the flow",
                step_id=step,
                details={
                    "flow_id": flow_id,
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        try:
            flow_data = state_manager.get("flow_data")  # Validates flow data exists
        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Flow data not found. Please restart the flow",
                step_id=step,
                details={
                    "flow_id": flow_id,
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        # Let StateManager validate service through state update
        if credex_service:
            try:
                success, error = state_manager.update_state({
                    "flow_data": {
                        "service": credex_service  # StateManager validates service structure
                    }
                })
                if not success:
                    error_context = ErrorContext(
                        error_type="state",
                        message="Failed to validate service. Please try again",
                        step_id=step,
                        details={
                            "flow_id": flow_id,
                            "error": error
                        }
                    )
                    raise StateException(ErrorHandler.handle_error(
                        StateException(error),
                        state_manager,
                        error_context
                    ))
            except Exception as e:
                error_context = ErrorContext(
                    error_type="state",
                    message="Failed to update service state. Please try again",
                    step_id=step,
                    details={
                        "flow_id": flow_id,
                        "error": str(e)
                    }
                )
                raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        # Log validation success
        logger.info(
            "Flow step validation successful",
            extra={
                "flow_id": flow_id,
                "step": step,
                "channel_id": state_manager.get("channel")["identifier"]
            }
        )

        # Return step data for handler
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
            message="Failed to process flow step. Please try again",
            step_id=step,
            details={
                "flow_id": flow_id,
                "error": str(e),
                "input_data": input_data
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
