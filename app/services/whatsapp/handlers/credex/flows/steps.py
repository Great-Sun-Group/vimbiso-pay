"""Step processing for credex flows enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict, Optional

from core.components.input import SelectInput, ConfirmInput
from core.utils.exceptions import FlowException, SystemException


def process_step(state_manager: Any, step: str, input_data: Any, action: str) -> Optional[Dict]:
    """Process step input with validation

    Args:
        state_manager: State manager instance
        step: Current step
        input_data: Input value
        action: Action type (accept/decline/cancel)

    Returns:
        Step result or None if invalid
    """
    try:
        # Process step with proper component validation
        if step == "select":
            # Get offers from state
            flow_data = state_manager.get_flow_state()
            offers = flow_data.get("data", {}).get("offers", [])

            # Validate selection through component
            select_component = SelectInput([str(i+1) for i in range(len(offers))])
            result = select_component.validate(input_data)
            if "error" in result:
                return result

            # Convert to verified data
            select_data = select_component.to_verified_data(input_data)
            selected_index = int(select_data["selected_id"]) - 1
            selected_offer = offers[selected_index]

            # Update state with selection
            state_manager.update_state({
                "flow_data": {
                    "data": {
                        "credex_id": selected_offer["id"],
                        "amount": selected_offer["formattedInitialAmount"],
                        "counterparty": selected_offer["counterpartyAccountName"]
                    },
                    "step": "confirm"
                }
            })

            return {
                "success": True,
                "credex_id": selected_offer["id"]
            }

        elif step == "confirm":
            # Validate confirmation through component
            confirm_component = ConfirmInput()
            result = confirm_component.validate(input_data)
            if "error" in result:
                return result

            # Convert to verified data
            confirm_data = confirm_component.to_verified_data(input_data)

            # Return confirmation result
            return {
                "success": True,
                "confirmed": confirm_data["confirmed"]
            }

        return None

    except FlowException:
        # Let flow errors propagate up
        raise

    except Exception as e:
        # Wrap unexpected errors as system errors
        raise SystemException(
            message=str(e),
            code="STEP_ERROR",
            service="credex_steps",
            action=f"{action}_{step}",
            details={
                "step": step,
                "input": input_data
            }
        )
