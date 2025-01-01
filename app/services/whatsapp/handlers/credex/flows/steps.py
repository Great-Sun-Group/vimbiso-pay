"""Flow step processing with state validation through StateManager"""
from typing import Any, Optional

from .constants import VALID_DENOMINATIONS


def process_step(state_manager: Any, step: str, input_data: Optional[Any] = None) -> None:
    """Process flow step input with validation through state updates

    Args:
        state_manager: Manages state validation and updates
        step: Current step name
        input_data: Step input to validate
    """
    # Skip empty input - let flow handle initial prompts
    if not input_data:
        return

    # Build state update matching validator structure
    if step == "amount":
        # Parse amount and denomination
        amount_str = str(input_data).strip()
        parts = amount_str.split()

        # Handle different formats (e.g. "100 USD" or "USD 100")
        if len(parts) == 2:
            value, denom = (float(parts[0]), parts[1]) if parts[1] in VALID_DENOMINATIONS else (float(parts[1]), parts[0])
        else:
            value, denom = float(amount_str), "USD"  # Default to USD

        state_update = {
            "flow_data": {
                "data": {
                    "amount": {
                        "value": value,
                        "denomination": denom
                    }
                }
            }
        }

    elif step == "handle":
        state_update = {
            "flow_data": {
                "data": {
                    "handle": str(input_data)
                }
            }
        }

    elif step == "confirm":
        state_update = {
            "flow_data": {
                "data": {
                    "confirmed": input_data == "confirm"
                }
            }
        }

    else:
        # For other steps, just store the input
        state_update = {
            "flow_data": {
                "data": {
                    step: str(input_data)
                }
            }
        }

    # Update state - validation handled by StateManager
    state_manager.update_state(state_update)
