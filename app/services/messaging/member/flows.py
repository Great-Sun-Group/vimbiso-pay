"""Member flows using messaging service interface"""
import logging
from typing import Any, Dict, Optional

from core.api.auth_client import login
from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import Message, TextContent
from core.utils.exceptions import FlowException, SystemException

from ..utils import get_recipient

logger = logging.getLogger(__name__)


class AuthFlow:
    """Authentication flow"""

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get auth step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step("member_auth", step)
        return ""

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process auth step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("member_auth", step)

            if step == "greeting":
                # Create greeting component
                from core.components.registry import create_component
                component = create_component("Greeting")

                # Validate and get greeting
                validation_result = component.validate({})
                if not validation_result.valid:
                    raise FlowException(
                        message="Failed to generate greeting",
                        step="greeting",
                        action="validate",
                        data={"validation": validation_result.error}
                    )

                # Send greeting with proper message structure
                recipient = get_recipient(state_manager)
                return Message(
                    recipient=recipient,
                    content=TextContent(
                        body=component.to_message_content(validation_result.value)
                    )
                )

            elif step == "login":
                # Attempt login
                success, auth_details = login(state_manager.get_channel_id())

                if success:
                    # Validate auth details
                    if not auth_details.get("token") or not auth_details.get("memberID"):
                        raise FlowException(
                            message="Invalid auth details",
                            step="login",
                            action="validate_auth",
                            data={"auth": auth_details}
                        )

                    # Get full response data for state update
                    from core.api.auth_client import get_login_response_data
                    response_data = get_login_response_data()

                    if not response_data:
                        raise FlowException(
                            message="Failed to get login response data",
                            step="login",
                            action="get_response",
                            data={"auth": auth_details}
                        )

                    # Wipe all existing state before updating with new login
                    state_manager.update_state({
                        "flow_data": {},
                        "dashboard": None,
                        "active_account_id": None
                    })

                    # Update profile state through proper validation
                    from core.api.profile import update_profile_from_response
                    profile_updated = update_profile_from_response(
                        api_response=response_data,
                        state_manager=state_manager,
                        action_type="login",
                        update_from="auth_flow",
                        token=auth_details["token"]
                    )

                    if not profile_updated:
                        raise FlowException(
                            message="Failed to update profile state",
                            step="login",
                            action="update_profile",
                            data={"response": response_data}
                        )

                    # Get account handler for dashboard
                    from ..account.handlers import AccountHandler
                    account_handler = AccountHandler(messaging_service)

                    # Start dashboard flow
                    return account_handler.start_dashboard(state_manager)

                else:
                    # Return registration message
                    recipient = get_recipient(state_manager)
                    return Message(
                        recipient=recipient,
                        content=TextContent(body=auth_details.get("message"))
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
                message=f"Error in auth flow: {str(e)}",
                code="FLOW_ERROR",
                service="auth_flow",
                action=f"process_{step}"
            )


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
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process upgrade step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("member_upgrade", step)
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
                    return Message(
                        recipient=recipient,
                        content=TextContent(body="❌ Upgrade cancelled.")
                    )

                # Update state
                state_manager.update_state({
                    "flow_data": {
                        "data": {"confirmed": True}
                    }
                })

                # Return completion message
                return Message(
                    recipient=recipient,
                    content=TextContent(
                        body=UpgradeFlow.get_step_content("complete")
                    )
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
                message=f"Error in upgrade flow: {str(e)}",
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
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process registration step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("member_registration", step)
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

                # Return next step message
                return Message(
                    recipient=recipient,
                    content=TextContent(
                        body=RegistrationFlow.get_step_content("lastname")
                    )
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

                # Return completion message
                return Message(
                    recipient=recipient,
                    content=TextContent(
                        body=RegistrationFlow.get_step_content("complete", {
                            "firstname": state_manager.get_flow_data().get("firstname"),
                            "lastname": input_value
                        })
                    )
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
                message=f"Error in registration flow: {str(e)}",
                code="FLOW_ERROR",
                service="member_flow",
                action=f"process_{step}"
            )
