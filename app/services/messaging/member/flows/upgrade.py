"""Upgrade flow implementation"""
import logging
from typing import Any, Dict, Optional

from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import Message, TextContent
from core.utils.exceptions import FlowException, SystemException

from ...utils import get_recipient

logger = logging.getLogger(__name__)


class UpgradeFlow:
    """Member tier upgrade flow"""

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get upgrade step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step("member_upgrade", step)

        if step == "confirm":
            return (
                "⭐ Upgrade Member Tier\n"
                "This will upgrade your account to the next tier level.\n"
                "Please confirm (yes/no):"
            )
        elif step == "complete":
            if data and data.get("new_tier"):
                return f"✅ Successfully upgraded to Tier {data['new_tier']}!"
            return "✅ Upgrade completed successfully!"
        return ""

    @staticmethod
    def _handle_confirm(state_manager: Any, input_value: str) -> bool:
        """Handle confirmation step"""
        # Validate confirmation
        if not isinstance(input_value, str):
            raise FlowException(
                message="Invalid confirmation input",
                step="confirm",
                action="validate",
                data={"value": input_value}
            )

        confirmed = input_value.lower() in ["yes", "y"]
        if confirmed:
            # Update state
            state_manager.update_state({
                "flow_data": {
                    "data": {"confirmed": True}
                }
            })

        return confirmed

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process upgrade step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("member_upgrade", step)
            recipient = get_recipient(state_manager)

            if step == "confirm":
                # If no input value, this is the initial confirm step
                if input_value is None:
                    # Get and send initial confirmation message
                    confirm_content = UpgradeFlow.get_step_content("confirm")
                    return Message(
                        recipient=recipient,
                        content=TextContent(body=confirm_content)
                    )

                # Otherwise handle the confirmation response
                confirmed = UpgradeFlow._handle_confirm(state_manager, input_value)
                if not confirmed:
                    # Create message with static content
                    cancel_message = "❌ Upgrade cancelled."
                    return Message(
                        recipient=recipient,
                        content=TextContent(body=cancel_message)
                    )

                # Return completion message
                completion_content = UpgradeFlow.get_step_content("complete")
                return Message(
                    recipient=recipient,
                    content=TextContent(body=completion_content)
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except FlowException:
            raise

        except Exception as e:
            raise SystemException(
                message=f"Error in upgrade flow: {str(e)}",
                code="FLOW_ERROR",
                service="member_flow",
                action=f"process_{step}"
            )
