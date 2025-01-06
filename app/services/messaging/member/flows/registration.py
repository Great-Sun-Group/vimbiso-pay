"""Registration flow implementation"""
import logging
from typing import Any, Dict, Optional

from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import Message, TextContent
from core.utils.exceptions import FlowException, SystemException

from ...utils import get_recipient

logger = logging.getLogger(__name__)


class RegistrationFlow:
    """Member registration flow"""

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get registration step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step("member_registration", step)

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
    def _handle_firstname(state_manager: Any, input_value: str) -> None:
        """Handle firstname step"""
        # Validate first name
        if not input_value or len(input_value) < 2:
            raise FlowException(
                message="First name must be at least 2 characters",
                step="firstname",
                action="validate",
                data={"value": input_value}
            )

        # Update state
        state_manager.update_state({
            "flow_data": {
                "data": {"firstname": input_value}
            }
        })

    @staticmethod
    def _handle_lastname(state_manager: Any, input_value: str) -> None:
        """Handle lastname step"""
        # Validate last name
        if not input_value or len(input_value) < 2:
            raise FlowException(
                message="Last name must be at least 2 characters",
                step="lastname",
                action="validate",
                data={"value": input_value}
            )

        # Update state
        state_manager.update_state({
            "flow_data": {
                "data": {"lastname": input_value}
            }
        })

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process registration step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("member_registration", step)
            recipient = get_recipient(state_manager)

            # Process step
            if step == "firstname":
                # Handle firstname step
                RegistrationFlow._handle_firstname(state_manager, input_value)

                # Get and validate next step content
                next_step_content = RegistrationFlow.get_step_content("lastname")
                if not isinstance(next_step_content, str):
                    raise FlowException(
                        message="Invalid next step content type",
                        step="firstname",
                        action="format_content",
                        data={"content_type": type(next_step_content).__name__}
                    )

                return Message(
                    recipient=recipient,
                    content=TextContent(body=next_step_content)
                )

            elif step == "lastname":
                # Handle lastname step
                RegistrationFlow._handle_lastname(state_manager, input_value)

                # Get and validate completion content
                completion_data = {
                    "firstname": state_manager.get_flow_data().get("firstname"),
                    "lastname": input_value
                }
                completion_content = RegistrationFlow.get_step_content("complete", completion_data)
                if not isinstance(completion_content, str):
                    raise FlowException(
                        message="Invalid completion content type",
                        step="complete",
                        action="format_content",
                        data={"content_type": type(completion_content).__name__}
                    )

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
                message=f"Error in registration flow: {str(e)}",
                code="FLOW_ERROR",
                service="member_flow",
                action=f"process_{step}"
            )
