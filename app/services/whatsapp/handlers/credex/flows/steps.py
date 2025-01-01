"""Generic step processing functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException

from .transformers import transform_button_input, transform_handle

logger = logging.getLogger(__name__)

# Valid action types
VALID_ACTIONS = {"cancel", "accept", "decline", "registration", "upgrade"}


def validate_step_sequence(state_manager: Any, step: str) -> None:
    """Validate step sequence before processing"""
    flow_data = state_manager.get("flow_data")
    if not flow_data:
        raise StateException("missing_flow_data")

    # Define valid sequence including complete
    STEPS = ["amount", "handle", "confirm", "complete"]
    current_step = flow_data.get("current_step")
    step_num = flow_data.get("step", 0)

    # Special handling for complete step
    if current_step == "complete":
        if step != "complete" or step_num != 3:
            raise StateException("invalid_complete_step")
        return

    # Validate step matches sequence for non-complete steps
    if step_num >= len(STEPS) - 1 or STEPS[step_num] != step:  # -1 to exclude complete
        raise StateException("invalid_step_sequence")

    # Validate current step matches for non-complete steps
    if current_step != step:
        raise StateException("invalid_current_step")


def cleanup_step_data(state_manager: Any, step: str, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean old data when updating state"""
    flow_data = state_manager.get("flow_data")
    if not flow_data:
        return new_data

    # Keep only relevant previous data
    clean_data = {}
    if step == "handle":
        clean_data["amount"] = flow_data.get("data", {}).get("amount")
    elif step == "confirm":
        clean_data.update({
            "amount": flow_data.get("data", {}).get("amount"),
            "handle": flow_data.get("data", {}).get("handle")
        })

    # Add new data
    clean_data.update(new_data)
    return clean_data


def validate_step_input(state_manager: Any, step: str, input_data: Any, action: Optional[str] = None) -> Dict[str, Any]:
    """Validate step input through state manager"""
    # Validate step sequence first
    validate_step_sequence(state_manager, step)

    if step == "amount":
        # Parse amount input
        amount_str = str(input_data).strip().upper()
        parts = amount_str.split()

        # Handle different formats
        if len(parts) == 1:
            # Just number - use USD default
            try:
                amount = float(parts[0])
                denomination = "USD"
            except ValueError:
                raise StateException("invalid_amount_format")
        elif len(parts) == 2:
            # Check if denomination is first or second
            if parts[0] in {"USD", "ZWG", "XAU", "CAD"}:
                denomination = parts[0]
                try:
                    amount = float(parts[1])
                except ValueError:
                    raise StateException("invalid_amount_format")
            else:
                try:
                    amount = float(parts[0])
                    denomination = parts[1]
                except ValueError:
                    raise StateException("invalid_amount_format")
        else:
            raise StateException("invalid_amount_format")

        # Validate amount with state context
        from .offer import validate_offer_amount
        validate_offer_amount(amount, denomination, state_manager)

        # Create standard structure using step name
        result = {
            "amount": {  # Standard key using step name
                "value": amount,
                "denomination": denomination
            }
        }

        # Store with standard structure and advance step
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "offer",  # Set initial flow type
                "step": 1,  # Advance to next step
                "current_step": "handle",  # Move to handle step
                "data": result
            }
        })
        if not success:
            logger.error(
                "Failed to update flow state",
                extra={
                    "error": error,
                    "result": result,
                    "step": "amount"
                }
            )
            raise StateException(f"Failed to update flow state: {error}")

        return result

    elif step == "handle":
        # Get current flow data first to ensure we have amount
        flow_data = state_manager.get("flow_data") or {}
        flow_data_dict = flow_data.get("data", {})

        # Debug log state in handle step
        logger.debug(
            "Validating handle step",
            extra={
                "flow_data": flow_data,
                "flow_data_dict": flow_data_dict,
                "input": input_data,
                "step": step
            }
        )

        # Validate previous step data using standard structure
        if not flow_data_dict.get("amount", {}).get("value"):
            logger.error(
                "Missing amount in handle step",
                extra={
                    "flow_data": flow_data,
                    "flow_data_dict": flow_data_dict,
                    "input": input_data
                }
            )
            raise StateException("missing_amount")

        # Transform and validate handle
        validated = transform_handle(input_data, state_manager)

        # Clean and update state
        clean_data = cleanup_step_data(state_manager, "handle", {"handle": validated})
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "offer",  # Ensure flow type stays as offer
                "step": 2,  # Advance to next step
                "current_step": "confirm",  # Move to confirm step
                "data": clean_data
            }
        })
        if not success:
            logger.error(
                "Failed to update flow state",
                extra={
                    "error": error,
                    "handle": validated,
                    "step": "handle"
                }
            )
            raise StateException(f"Failed to update flow state: {error}")
        return {"handle": validated}

    elif step == "confirm":
        # Get current flow data first to ensure we have required data
        flow_data = state_manager.get("flow_data") or {}
        flow_data_dict = flow_data.get("data", {})

        # Validate required data using standard structure
        if not flow_data_dict.get("amount", {}).get("value"):
            raise StateException("missing_amount")
        if not flow_data_dict.get("handle"):
            raise StateException("missing_handle")

        # Only validate button input if provided
        if input_data:
            button_id = transform_button_input(input_data, state_manager)
            if not button_id or button_id not in ["confirm", "cancel"]:
                raise StateException("invalid_button")
            confirmed = button_id == "confirm"

            # Clean and update state
            clean_data = cleanup_step_data(state_manager, "confirm", {"confirmed": confirmed})
            # Update step number based on confirmation
            next_step = 2 if not confirmed else 3  # Advance to step 3 for complete
            next_step_name = "confirm" if not confirmed else "complete"

            success, error = state_manager.update_state({
                "flow_data": {
                    "flow_type": "offer",  # Ensure flow type stays as offer
                    "step": next_step,  # Advance step number with current_step
                    "current_step": next_step_name,
                    "data": clean_data
                }
            })
            if not success:
                logger.error(
                    "Failed to update flow state",
                    extra={
                        "error": error,
                        "confirmed": confirmed,
                        "step": "confirm"
                    }
                )
                raise StateException(f"Failed to update flow state: {error}")
            return {"confirmed": confirmed}
        else:
            # No input yet, just validate required data exists
            return None

    elif step == "select" and action:
        if not input_data.startswith(f"{action}_"):
            raise StateException("invalid_selection")

        credex_id = input_data[len(action) + 1:]
        if not credex_id:
            raise StateException("invalid_selection")

        # Update only what changes
        success, error = state_manager.update_state({
            "flow_data": {
                "data": {
                    "credex_id": credex_id,
                    "action_type": action
                }
            }
        })
        if not success:
            logger.error(
                "Failed to update flow state",
                extra={
                    "error": error,
                    "credex_id": credex_id,
                    "action": action,
                    "step": "confirm"
                }
            )
            raise StateException(f"Failed to update flow state: {error}")
        return {"credex_id": credex_id}

    raise StateException("invalid_step")


def process_step(state_manager: Any, step: str, input_data: Any = None, action: Optional[str] = None) -> Dict[str, Any]:
    """Process step input with validation"""
    try:
        # Return None for initial prompt
        if not input_data:
            return None

        # Validate action if provided
        if action and action not in VALID_ACTIONS:
            raise StateException("invalid_action")

        # Validate and store input
        return validate_step_input(state_manager, step, input_data, action)

    except Exception as e:
        # Create proper error context
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id=step,
            details={
                "input": input_data,
                "flow_data": state_manager.get("flow_data"),
                "action": action
            }
        )
        # Let error handler create proper message
        return ErrorHandler.handle_flow_error(
            state_manager,
            e,
            error_context,
            return_message=True
        )
