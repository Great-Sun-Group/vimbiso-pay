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


def validate_step_input(state_manager: Any, step: str, input_data: Any, action: Optional[str] = None) -> Dict[str, Any]:
    """Validate step input through state manager"""
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
                raise StateException("Invalid amount format. Please enter a valid number with optional denomination")
        elif len(parts) == 2:
            # Check if denomination is first or second
            if parts[0] in {"USD", "ZWG", "XAU", "CAD"}:
                denomination = parts[0]
                try:
                    amount = float(parts[1])
                except ValueError:
                    raise StateException("Invalid amount format. Please enter a valid number with optional denomination")
            else:
                try:
                    amount = float(parts[0])
                    denomination = parts[1]
                except ValueError:
                    raise StateException("Invalid amount format. Please enter a valid number with optional denomination")
        else:
            raise StateException("Invalid amount format. Please enter a valid number with optional denomination")

        # Validate amount
        if denomination not in {"USD", "ZWG", "XAU", "CAD"}:
            raise StateException("Invalid denomination. Supported: USD, ZWG, XAU, CAD")
        if amount <= 0:
            raise StateException("Amount must be greater than 0")

        # Store validated amount in state
        result = {
            "amount": amount,
            "denomination": denomination
        }
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}
        current_step = flow_data.get("step", 0)

        # Validate and store amount through state update
        state_manager.update_state({
            "flow_data": {
                "flow_type": flow_data.get("flow_type", "offer"),
                "step": current_step + 1,  # Increment step
                "current_step": "handle",   # Move to next step
                "data": {
                    **(flow_data.get("data", {})),  # Preserve existing data
                    "amount": result,               # Add new data
                    "last_completed": "amount"      # Track completion
                },
                "validation": {                     # Track validation
                    "amount": True,
                    "timestamp": flow_data.get("validation", {}).get("timestamp")
                }
            }
        })
        return result

    elif step == "handle":
        validated = transform_handle(input_data)
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}
        current_step = flow_data.get("step", 0)

        # Validate and store handle through state update
        state_manager.update_state({
            "flow_data": {
                "flow_type": flow_data.get("flow_type", "offer"),
                "step": current_step + 1,  # Increment step
                "current_step": "confirm",  # Move to next step
                "data": {
                    **(flow_data.get("data", {})),  # Preserve existing data
                    "handle": validated,            # Add new data
                    "last_completed": "handle"      # Track completion
                },
                "validation": {                     # Track validation
                    "amount": flow_data.get("validation", {}).get("amount"),
                    "handle": True,
                    "timestamp": flow_data.get("validation", {}).get("timestamp")
                }
            }
        })
        return validated

    elif step == "confirm":
        # Transform and validate button input
        button_id = transform_button_input(input_data, state_manager)
        if not button_id or button_id not in ["confirm", "cancel"]:
            raise StateException("Please use the Confirm or Cancel button")
        confirmed = button_id == "confirm"
        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}
        current_step = flow_data.get("step", 0)

        # Process confirmation through state update
        state_manager.update_state({
            "flow_data": {
                "flow_type": flow_data.get("flow_type", "offer"),
                "step": current_step + (1 if confirmed else 0),  # Only increment if confirmed
                "current_step": "complete" if confirmed else "confirm",
                "data": {
                    **(flow_data.get("data", {})),    # Preserve existing data
                    "confirmed": confirmed,           # Add confirmation
                    "last_completed": "confirm" if confirmed else flow_data.get("data", {}).get("last_completed")
                },
                "validation": {                       # Track validation
                    "amount": flow_data.get("validation", {}).get("amount"),
                    "handle": flow_data.get("validation", {}).get("handle"),
                    "confirmed": confirmed,
                    "timestamp": flow_data.get("validation", {}).get("timestamp")
                }
            }
        })
        return {"confirmed": confirmed}

    elif step == "select" and action:
        if not input_data.startswith(f"{action}_"):
            raise StateException("Invalid selection. Please select from the list")

        credex_id = input_data[len(action) + 1:]
        if not credex_id:
            raise StateException("Invalid selection. Please select from the list")

        # Get current flow data
        flow_data = state_manager.get("flow_data") or {}
        current_step = flow_data.get("step", 0)

        # Validate and store selection through state update
        state_manager.update_state({
            "flow_data": {
                "flow_type": flow_data.get("flow_type", "offer"),
                "step": current_step + 1,  # Increment step
                "current_step": "confirm",  # Move to next step
                "data": {
                    **(flow_data.get("data", {})),  # Preserve existing data
                    "credex_id": credex_id,         # Add selection data
                    "action_type": action,
                    "last_completed": "select"      # Track completion
                },
                "validation": {                     # Track validation
                    "amount": flow_data.get("validation", {}).get("amount"),
                    "handle": flow_data.get("validation", {}).get("handle"),
                    "select": True,
                    "timestamp": flow_data.get("validation", {}).get("timestamp")
                }
            }
        })
        return {"credex_id": credex_id}

    raise StateException(f"Invalid step: {step}")


def process_step(state_manager: Any, step: str, input_data: Any = None, action: Optional[str] = None) -> Dict[str, Any]:
    """Process step input with validation"""
    try:
        # Return None for initial prompt
        if not input_data:
            return None

        # Validate action if provided
        if action and action not in VALID_ACTIONS:
            error_context = ErrorContext(
                error_type="input",
                message=f"Invalid action type: {action}",
                details={
                    "action": action,
                    "valid_actions": list(VALID_ACTIONS)
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException("Invalid action"),
                state_manager,
                error_context
            ))

        # Validate and store input
        return validate_step_input(state_manager, step, input_data, action)

    except Exception as e:
        # Only include step_id for flow errors
        error_type = "flow" if isinstance(e, StateException) else "system"
        error_context = ErrorContext(
            error_type=error_type,
            message=str(e),
            step_id=step if error_type == "flow" else None,
            details={
                "input": input_data,
                "action": action,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
