"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict, Optional

from core.components.input import AmountInput, HandleInput, ConfirmInput
from core.utils.exceptions import FlowException, SystemException
from services.credex.service import get_credex_service

from .constants import VALID_DENOMINATIONS


def get_step_content(step: str, data: Optional[Dict] = None) -> str:
    """Get step content without channel formatting"""
    if step == "amount":
        return (
            "💸 What offer amount and denomination?\n"
            "- Defaults to USD 💵 (1, 73932.64)\n"
            "- Valid denom placement ✨ (54 ZWG, ZWG 125.54)\n"
            f"- Valid denoms 🌐 {', '.join(sorted(VALID_DENOMINATIONS))}"
        )
    elif step == "handle":
        return "Enter account 💳 handle:"
    elif step == "confirm" and data:
        return (
            "📝 Review your offer:\n"
            f"💸 Amount: {data.get('amount')}\n"
            f"💳 To: {data.get('handle')}"
        )
    elif step == "complete":
        return "✅ Your offer has been sent."
    return ""


def process_offer_step(state_manager: Any, step: str, input_data: Any = None) -> Dict:
    """Process offer step and return appropriate message"""
    try:
        # Handle initial prompts
        if not input_data:
            if step == "amount":
                return {
                    "success": True,
                    "content": get_step_content("amount")
                }
            elif step == "handle":
                return {
                    "success": True,
                    "content": get_step_content("handle")
                }
            elif step == "complete":
                return {
                    "success": True,
                    "content": get_step_content("complete")
                }

            raise FlowException(
                message="Invalid step for prompt",
                step=step,
                action="prompt",
                data={"step": step}
            )

        # Process step with proper component validation
        if step == "amount":
            # Validate amount through component
            amount_component = AmountInput()
            result = amount_component.validate(input_data)
            if "error" in result:
                return result

            # Convert to verified data
            amount_data = amount_component.to_verified_data(input_data)

            # Update state with verified data
            state_manager.update_state({
                "flow_data": {
                    "data": amount_data,
                    "step": "handle"
                }
            })

            return {
                "success": True,
                "content": get_step_content("handle")
            }

        elif step == "handle":
            # Validate handle through component
            handle_component = HandleInput()
            result = handle_component.validate(input_data)
            if "error" in result:
                return result

            # Convert to verified data
            handle_data = handle_component.to_verified_data(input_data)

            # Get amount from state
            flow_data = state_manager.get_flow_state()
            amount_data = flow_data.get("data", {}).get("amount")
            if not amount_data:
                raise FlowException(
                    message="Missing amount data",
                    step=step,
                    action="validate",
                    data={"step": step}
                )

            # Update state with verified data
            state_manager.update_state({
                "flow_data": {
                    "data": {
                        "amount": amount_data,
                        "handle": handle_data["handle"]
                    },
                    "step": "confirm"
                }
            })

            return {
                "success": True,
                "content": get_step_content("confirm", {
                    "amount": amount_data,
                    "handle": handle_data["handle"]
                }),
                "actions": ["confirm", "cancel"]
            }

        elif step == "confirm":
            # Validate confirmation through component
            confirm_component = ConfirmInput()
            result = confirm_component.validate(input_data)
            if "error" in result:
                return result

            # Convert to verified data
            confirm_data = confirm_component.to_verified_data(input_data)

            if confirm_data["confirmed"]:
                # Get flow data
                flow_data = state_manager.get_flow_state()
                offer_data = flow_data.get("data", {})

                if not offer_data.get("amount") or not offer_data.get("handle"):
                    raise FlowException(
                        message="Missing offer data",
                        step=step,
                        action="validate",
                        data={"step": step}
                    )

                try:
                    # Submit through service layer
                    credex_service = get_credex_service(state_manager)
                    success, response = credex_service["offer_credex"](state_manager)

                    if not success:
                        raise SystemException(
                            message=response.get("message", "Failed to create offer"),
                            code="OFFER_CREATE_FAILED",
                            service="credex",
                            action="create_offer"
                        )

                    # Update state with completion
                    state_manager.update_state({
                        "flow_data": {
                            "data": {
                                **offer_data,
                                "offer_id": response["offer_id"]
                            },
                            "step": "complete"
                        }
                    })

                    return {
                        "success": True,
                        "content": get_step_content("complete")
                    }

                except (FlowException, SystemException):
                    # Let flow and system errors propagate up
                    raise
                except Exception as e:
                    raise SystemException(
                        message=str(e),
                        code="OFFER_ERROR",
                        service="credex",
                        action="create_offer"
                    )

            # Show confirmation again if not confirmed
            flow_data = state_manager.get_flow_state()
            offer_data = flow_data.get("data", {})

            return {
                "success": True,
                "content": get_step_content("confirm", offer_data),
                "actions": ["confirm", "cancel"]
            }

        raise FlowException(
            message="Invalid step",
            step=step,
            action="process",
            data={"step": step}
        )

    except (FlowException, SystemException):
        # Let flow and system errors propagate up
        raise
    except Exception as e:
        raise SystemException(
            message=str(e),
            code="FLOW_ERROR",
            service="offer_flow",
            action=step
        )
