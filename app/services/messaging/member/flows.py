"""Member flows using messaging service interface"""
import logging
from typing import Any, Dict, Optional

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import ComponentException, FlowException, SystemException
from core.messaging.registry import FlowRegistry

logger = logging.getLogger(__name__)


def get_recipient(state_manager: Any) -> MessageRecipient:
    """Get message recipient from state with validation"""
    try:
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=state_manager.get_member_id()
        )
    except ComponentException:
        # If member_id fails, still return with channel_id
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=None
        )


class UpgradeFlow:
    """Member tier upgrade flow"""

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get upgrade step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step("upgrade", step)

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
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process upgrade step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("upgrade", step)
            recipient = get_recipient(state_manager)

            if step == "confirm":
                # Validate confirmation
                if not isinstance(input_value, str):
                    raise FlowException(
                        message="Invalid confirmation input",
                        step=step,
                        action="validate",
                        data={"value": input_value}
                    )

                confirmed = input_value.lower() in ["yes", "y"]
                if not confirmed:
                    return messaging_service.send_text(
                        recipient=recipient,
                        text="❌ Upgrade cancelled."
                    )

                # Update state
                state_manager.update_state({
                    "flow_data": {
                        "data": {"confirmed": True}
                    }
                })

                # Send completion message
                return messaging_service.send_text(
                    recipient=recipient,
                    text=UpgradeFlow.get_step_content("complete")
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except FlowException:
            # Let flow errors propagate up
            raise

        except Exception as e:
            # Wrap other errors
            raise SystemException(
                message=str(e),
                code="FLOW_ERROR",
                service="member_flow",
                action=f"process_{step}"
            )


class RegistrationFlow:
    """Member registration flow"""

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get registration step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step("registration", step)

        if step == "welcome":
            return (
                "👋 Welcome to VimbisoPay!\n"
                "Let's get you registered. First, I'll need some information."
            )
        elif step == "firstname":
            return "👤 What is your first name?"
        elif step == "lastname":
            return "👤 What is your last name?"
        elif step == "complete":
            if data:
                return (
                    "✅ Registration complete!\n"
                    f"Welcome {data.get('firstname')} {data.get('lastname')}!\n"
                    "You can now start using VimbisoPay."
                )
            return "✅ Registration complete!"
        return ""

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process registration step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("registration", step)
            recipient = get_recipient(state_manager)

            # Process step
            if step == "firstname":
                # Validate and store first name
                if not input_value or len(input_value) < 2:
                    raise FlowException(
                        message="First name must be at least 2 characters",
                        step=step,
                        action="validate",
                        data={"value": input_value}
                    )

                # Update state
                state_manager.update_state({
                    "flow_data": {
                        "data": {"firstname": input_value}
                    }
                })

                # Send next step
                return messaging_service.send_text(
                    recipient=recipient,
                    text=RegistrationFlow.get_step_content("lastname")
                )

            elif step == "lastname":
                # Validate and store last name
                if not input_value or len(input_value) < 2:
                    raise FlowException(
                        message="Last name must be at least 2 characters",
                        step=step,
                        action="validate",
                        data={"value": input_value}
                    )

                # Update state
                state_manager.update_state({
                    "flow_data": {
                        "data": {"lastname": input_value}
                    }
                })

                # Send completion message
                return messaging_service.send_text(
                    recipient=recipient,
                    text=RegistrationFlow.get_step_content("complete", {
                        "firstname": state_manager.get_flow_data().get("firstname"),
                        "lastname": input_value
                    })
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except FlowException:
            # Let flow errors propagate up
            raise

        except Exception as e:
            # Wrap other errors
            raise SystemException(
                message=str(e),
                code="FLOW_ERROR",
                service="member_flow",
                action=f"process_{step}"
            )
