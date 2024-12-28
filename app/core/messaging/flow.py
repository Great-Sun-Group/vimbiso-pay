"""Clean flow management implementation using pure functions"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StepType(Enum):
    """Types of interaction steps"""
    TEXT = "text"
    BUTTON = "button"
    LIST = "list"


@dataclass
class Step:
    """Single interaction step"""
    id: str
    type: StepType
    message: Union[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]]
    validator: Optional[Callable[[Any], bool]] = None
    transformer: Optional[Callable[[Any], Any]] = None


def validate_step(step: Step, input_data: Any) -> bool:
    """Validate step input"""
    try:
        # Special validation for confirmation
        if step.id == "confirm" and isinstance(input_data, dict):
            interactive = input_data.get("interactive", {})
            if (interactive.get("type") == "button_reply" and
                    interactive.get("button_reply", {}).get("id") == "confirm_action"):
                return True
            return False

        # Use custom validator if provided
        if not step.validator:
            return True

        try:
            return step.validator(input_data)
        except Exception as validation_error:
            logger.error(
                f"Validation failed in step {step.id}",
                extra={
                    "step_id": step.id,
                    "validator": step.validator.__name__ if hasattr(step.validator, '__name__') else str(step.validator),
                    "input": input_data,
                    "error": str(validation_error)
                },
                exc_info=True
            )
            raise ValueError(f"Validation error in step {step.id}: {str(validation_error)}")

    except Exception as e:
        if not isinstance(e, ValueError):
            logger.error(f"Unexpected error in step {step.id}: {str(e)}")
        raise


def transform_step_input(step: Step, input_data: Any) -> Any:
    """Transform step input"""
    try:
        return step.transformer(input_data) if step.transformer else input_data
    except Exception as e:
        logger.error(f"Transform error in {step.id}: {str(e)}")
        raise ValueError(str(e))


def get_step_message(step: Step, state_manager: Any) -> Dict[str, Any]:
    """Get step message using state manager"""
    try:
        flow_data = state_manager.get("flow_data", {})
        return step.message(flow_data) if callable(step.message) else step.message
    except Exception as e:
        logger.error(f"Message error in {step.id}: {str(e)}")
        raise ValueError(str(e))


def initialize_flow_state(
    state_manager: Any,
    flow_type: str,
    step: int = 0,
    current_step: str = "initial",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """Initialize or update flow state

    This is the central function for managing flow state. All flows should use this
    to initialize or update their state, ensuring consistent state management.

    Args:
        state_manager: State manager instance
        flow_type: Type of flow (e.g. "auth", "offer", "dashboard")
        step: Integer step number for progression tracking
        current_step: String step identifier for routing
        data: Optional initial data dictionary

    Raises:
        StateException: If state update fails
    """
    try:
        # Create complete flow state
        flow_state = {
            "flow_data": {
                "flow_type": flow_type,
                "step": step,
                "current_step": current_step,
                "data": data or {}
            }
        }

        # Update through StateManager
        success, error = state_manager.update_state(flow_state)
        if not success:
            raise StateException(f"Failed to initialize flow state: {error}")

        logger.debug("Flow state initialized:")
        logger.debug(f"- Flow type: {flow_type}")
        logger.debug(f"- Step: {step}")
        logger.debug(f"- Current step: {current_step}")
        logger.debug(f"- Member ID: {state_manager.get('member_id')}")

    except Exception as e:
        logger.error(f"Flow state initialization error: {str(e)}")
        raise StateException(str(e))


def get_current_step(state_manager: Any, steps: List[Step]) -> Optional[Step]:
    """Get current step from state"""
    current_step_index = state_manager.get("flow_data", {}).get("current_step", 0)
    return steps[current_step_index] if 0 <= current_step_index < len(steps) else None


def process_flow_input(
    state_manager: Any,
    flow_id: str,
    steps: List[Step],
    input_data: Any,
    complete_handler: Optional[Callable[[Any], Optional[Dict[str, Any]]]] = None
) -> Optional[Dict[str, Any]]:
    """Process flow input and return next message or None if complete"""
    # Validate state access at boundary
    validation = StateValidator.validate_before_access(
        {
            "member_id": state_manager.get("member_id"),
            "flow_data": state_manager.get("flow_data")
        },
        {"member_id", "flow_data"}
    )
    if not validation.is_valid:
        raise ValueError(validation.error_message)

    step = get_current_step(state_manager, steps)
    if not step:
        return None

    try:
        # Update validation state
        initialize_flow_state(
            state_manager,
            state_manager.get("flow_data", {}).get("flow_type", "unknown"),
            state_manager.get("flow_data", {}).get("step", 0),
            step.id,
            {
                "validation": {
                    "step_id": step.id,
                    "step_index": state_manager.get("flow_data", {}).get("current_step", 0),
                    "input": input_data,
                    "timestamp": audit.get_current_timestamp()
                }
            }
        )

        # Get current flow data for logging
        current_flow_data = state_manager.get("flow_data", {})

        # Log flow event
        audit.log_flow_event(
            flow_id,
            "step_start",
            step.id,
            current_flow_data,
            "in_progress"
        )

        # Validate input
        validation_result = validate_step(step, input_data)
        logger.debug(f"Input validation result: {validation_result}")

        if not validation_result:
            # Update validation state with error
            initialize_flow_state(
                state_manager,
                current_flow_data["flow_type"],
                current_flow_data["step"],
                step.id,
                {
                    "validation": {
                        "success": False,
                        "error": "Invalid input"
                    }
                }
            )

            # Log validation failure
            audit.log_flow_event(
                flow_id,
                "validation_error",
                step.id,
                current_flow_data,
                "failure",
                "Invalid input"
            )

            raise ValueError("Invalid input")

        # Transform input
        transformed_data = transform_step_input(step, input_data)

        # Store transformed input data
        next_step = steps[current_flow_data.get("step", 0) + 1] if current_flow_data.get("step", 0) + 1 < len(steps) else None
        initialize_flow_state(
            state_manager,
            current_flow_data["flow_type"],
            current_flow_data["step"] + 1,
            next_step.id if next_step else "complete",
            {
                step.id if step.id != "amount" else "amount_denom": transformed_data,
                "validation": {
                    "success": True,
                    "transformed": transformed_data
                }
            }
        )

        # Get updated flow data for logging and completion check
        current_flow_data = state_manager.get("flow_data", {})

        # Log successful state transition
        audit.log_flow_event(
            flow_id,
            "step_complete",
            step.id,
            current_flow_data,
            "success"
        )

        # Complete or get next message
        if current_flow_data.get("step", 0) >= len(steps):
            # Get final flow data for completion logging
            final_flow_data = state_manager.get("flow_data", {})

            # Log flow completion
            audit.log_flow_event(
                flow_id,
                "complete",
                None,
                final_flow_data,
                "success"
            )
            return complete_handler(state_manager) if complete_handler else None

        next_step = get_current_step(state_manager, steps)
        return get_step_message(next_step, state_manager) if next_step else None

    except ValueError as validation_error:
        # Update validation state with error
        current_flow_data = state_manager.get("flow_data", {})
        initialize_flow_state(
            state_manager,
            current_flow_data["flow_type"],
            current_flow_data["step"],
            step.id,
            {
                "validation": {
                    "success": False,
                    "error": str(validation_error)
                }
            }
        )

        # Log validation error
        audit.log_flow_event(
            flow_id,
            "validation_error",
            step.id,
            current_flow_data,
            "failure",
            str(validation_error)
        )

        raise

    except Exception as e:
        error_msg = f"Process error in {step.id}: {str(e)}"
        logger.error(error_msg)

        # Log error event
        audit.log_flow_event(
            flow_id,
            "process_error",
            step.id,
            state_manager.get("flow_data", {}),
            "failure",
            error_msg
        )

        raise ValueError(str(e))
