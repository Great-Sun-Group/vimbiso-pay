"""Step processing functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException
from .messages import (create_initial_prompt, create_handle_prompt,
                       create_confirmation_prompt)
from .transformers import transform_amount, transform_handle

logger = logging.getLogger(__name__)


def validate_step_input(state_manager: Any, step: str, input_data: Any) -> Dict[str, Any]:
    """Validate step input through state manager"""
    if step == "amount":
        validated = transform_amount(input_data)
        state_manager.update_state({
            "flow_data": {
                "step": 1,
                "current_step": "amount",
                "data": {
                    "amount": validated
                }
            }
        })
        return validated

    elif step == "handle":
        validated = transform_handle(input_data)
        state_manager.update_state({
            "flow_data": {
                "step": 2,
                "current_step": "handle",
                "data": {
                    "handle": validated
                }
            }
        })
        return validated

    elif step == "confirm":
        if not input_data or input_data.lower() not in ["yes", "no"]:
            raise StateException("Please enter 'yes' or 'no'")
        confirmed = input_data.lower() == "yes"
        state_manager.update_state({
            "flow_data": {
                "step": 3,
                "current_step": "confirm",
                "data": {
                    "confirmed": confirmed
                }
            }
        })
        return {"confirmed": confirmed}

    raise StateException(f"Invalid step: {step}")


def process_amount_step(state_manager: Any, input_data: Optional[str] = None) -> Dict[str, Any]:
    """Process amount step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Initial prompt
        if not input_data:
            return create_initial_prompt(state_manager.get("channel")["identifier"])

        # Validate and store input
        validate_step_input(state_manager, "amount", input_data)
        return create_handle_prompt(state_manager.get("channel")["identifier"])

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="amount",
            details={"input": input_data}
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def process_handle_step(state_manager: Any, input_data: Optional[str] = None) -> Dict[str, Any]:
    """Process handle step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Initial prompt
        if not input_data:
            return create_handle_prompt(state_manager.get("channel")["identifier"])

        # Validate and store input
        validate_step_input(state_manager, "handle", input_data)
        return create_confirmation_prompt(state_manager.get("channel")["identifier"])

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="handle",
            details={"input": input_data}
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def process_confirm_step(state_manager: Any, input_data: Optional[str] = None) -> Dict[str, Any]:
    """Process confirmation step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Initial prompt
        if not input_data:
            return create_confirmation_prompt(state_manager.get("channel")["identifier"])

        # Validate and store input
        validated = validate_step_input(state_manager, "confirm", input_data)

        # Return empty dict to signal completion
        if validated["confirmed"]:
            return {}

        # Re-prompt if not confirmed
        return create_confirmation_prompt(state_manager.get("channel")["identifier"])

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="confirm",
            details={"input": input_data}
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
