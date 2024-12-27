"""Clean flow management implementation using pure functions"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

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


def initialize_flow(state_manager: Any, flow_id: str, flow_type: Optional[str] = None) -> None:
    """Initialize flow data in state"""
    if not flow_type:
        return

    current_flow_data = state_manager.get("flow_data", {})
    if not current_flow_data.get("flow_type"):
        success, error = state_manager.update_state({
            "flow_data": {
                **current_flow_data,
                "flow_type": flow_type,
                "_validation_context": {},
                "_validation_state": {},
                "current_step": 0
            }
        })

    logger.debug(f"Flow {flow_id} initialized:")
    logger.debug(f"- Flow type: {flow_type}")
    logger.debug(f"- Member ID: {state_manager.get('member_id')}")


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
        # Create validation state
        validation_state = {
            "step_id": step.id,
            "step_index": state_manager.get("flow_data", {}).get("current_step", 0),
            "input": input_data,
            "timestamp": audit.get_current_timestamp()
        }

        # Update validation state
        flow_data = state_manager.get("flow_data", {})
        flow_data["_validation_state"] = validation_state
        success, error = state_manager.update_state({"flow_data": flow_data})
        if not success:
            raise ValueError(f"Failed to update flow data: {error}")

        # Log flow event
        audit.log_flow_event(
            flow_id,
            "step_start",
            step.id,
            flow_data,
            "in_progress"
        )

        # Validate input
        validation_result = validate_step(step, input_data)
        logger.debug(f"Input validation result: {validation_result}")

        if not validation_result:
            # Update validation state with error
            flow_data["_validation_state"]["success"] = False
            flow_data["_validation_state"]["error"] = "Invalid input"
            success, error = state_manager.update_state({"flow_data": flow_data})
            if not success:
                raise ValueError(f"Failed to update flow data: {error}")

            # Log validation failure
            audit.log_flow_event(
                flow_id,
                "validation_error",
                step.id,
                flow_data,
                "failure",
                "Invalid input"
            )

            raise ValueError("Invalid input")

        # Transform input
        transformed_data = transform_step_input(step, input_data)

        # Update flow data with transformed input
        flow_data[step.id if step.id != "amount" else "amount_denom"] = transformed_data
        flow_data["_validation_state"]["success"] = True
        flow_data["_validation_state"]["transformed"] = transformed_data
        flow_data["current_step"] = flow_data.get("current_step", 0) + 1
        success, error = state_manager.update_state({"flow_data": flow_data})
        if not success:
            raise ValueError(f"Failed to update flow data: {error}")

        # Log successful state transition
        audit.log_flow_event(
            flow_id,
            "step_complete",
            step.id,
            flow_data,
            "success"
        )

        # Complete or get next message
        if flow_data["current_step"] >= len(steps):
            # Log flow completion
            audit.log_flow_event(
                flow_id,
                "complete",
                None,
                flow_data,
                "success"
            )
            return complete_handler(state_manager) if complete_handler else None

        next_step = get_current_step(state_manager, steps)
        return get_step_message(next_step, state_manager) if next_step else None

    except ValueError as validation_error:
        # Update validation state with error
        flow_data = state_manager.get("flow_data", {})
        flow_data["_validation_state"]["success"] = False
        flow_data["_validation_state"]["error"] = str(validation_error)
        success, error = state_manager.update_state({"flow_data": flow_data})
        if not success:
            raise ValueError(f"Failed to update flow data: {error}")

        # Log validation error
        audit.log_flow_event(
            flow_id,
            "validation_error",
            step.id,
            flow_data,
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
