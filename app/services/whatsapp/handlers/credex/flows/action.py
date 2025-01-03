"""Action flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.exceptions import FlowException, SystemException
from services.credex.service import get_credex_service

from .steps import process_step

logger = logging.getLogger(__name__)


def get_step_content(step: str, action: str, data: Optional[Dict] = None) -> str:
    """Get step content without channel formatting"""
    if step == "select":
        if not data or not data.get("items"):
            return f"❌ No {action} offers available"

        message_parts = [f"📋 Select offer to {action}:"]
        for i, item in enumerate(data["items"], 1):
            amount = item.get("formattedInitialAmount", "Unknown amount")
            counterparty = item.get("counterpartyAccountName", "Unknown")
            message_parts.append(f"{i}. 💸 {amount} with 👤 {counterparty}")

        return "\n".join(message_parts)

    elif step == "confirm" and data:
        return (
            f"📝 Confirm {action}:\n"
            f"🆔 CredEx ID: {data.get('credex_id')}\n\n"
            "✅ Please confirm (yes/no):"
        )

    elif step == "complete":
        return "✅ Your request has been processed."

    return ""


def process_action_step(state_manager: Any, step: str, action: str, input_data: Any = None) -> Dict:
    """Process action step with validation"""
    try:
        # Let StateManager validate channel
        state_manager.update_state({
            "validation": {
                "type": "channel",
                "required": True
            }
        })

        # Process step input through generic step processor
        result = process_step(state_manager, step, input_data, action)

        # Handle initial prompts
        if not input_data:
            if step == "select":
                # Get pending offers through service
                credex_service = get_credex_service(state_manager)
                success, response = credex_service["get_pending_offers"](state_manager)

                if not success:
                    raise SystemException(
                        message=response.get("message", "Failed to get offers"),
                        code="OFFER_FETCH_FAILED",
                        service="credex",
                        action="get_offers"
                    )

                return {
                    "success": True,
                    "content": get_step_content("select", action, {"items": response["offers"]})
                }

            elif step == "confirm":
                flow_state = state_manager.get_flow_state()
                return {
                    "success": True,
                    "content": get_step_content("confirm", action, flow_state),
                    "actions": ["confirm", "cancel"]
                }

            elif step == "complete":
                return {
                    "success": True,
                    "content": get_step_content("complete", action)
                }

            raise FlowException(
                message="Invalid step for prompt",
                step=step,
                action="prompt",
                data={"action": action}
            )

        # Process step result
        if result:
            return result

        # Invalid step if we get here
        raise FlowException(
            message=f"Invalid step: {step}",
            step=step,
            action="validate_step",
            data={"action": action}
        )

    except (FlowException, SystemException):
        # Let flow and system errors propagate up
        raise

    except Exception as e:
        # Wrap unexpected errors as system errors
        raise SystemException(
            message=str(e),
            code="ACTION_ERROR",
            service="credex_action",
            action=action,
            details={
                "step": step,
                "input": input_data
            }
        )


def process_cancel_step(state_manager: Any, step: str, input_data: Any = None) -> Dict:
    """Process cancel step"""
    return process_action_step(state_manager, step, "cancel", input_data)


def process_accept_step(state_manager: Any, step: str, input_data: Any = None) -> Dict:
    """Process accept step"""
    return process_action_step(state_manager, step, "accept", input_data)


def process_decline_step(state_manager: Any, step: str, input_data: Any = None) -> Dict:
    """Process decline step"""
    return process_action_step(state_manager, step, "decline", input_data)
