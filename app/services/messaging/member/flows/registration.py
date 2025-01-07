"""Registration flow implementation"""
import logging
from typing import Any, Dict, Optional

from core.components import create_component
from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import Message, TextContent
from core.utils.exceptions import (ComponentException, FlowException,
                                   SystemException)

from ...utils import get_recipient

logger = logging.getLogger(__name__)


class RegistrationFlow:
    """Member registration flow"""

    @staticmethod
    def _handle_greeting(messaging_service: MessagingServiceInterface, state_manager: Any, component: Any) -> Message:
        """Handle greeting component

        Args:
            messaging_service: Service for sending messages
            state_manager: Manager for flow state
            component: Greeting component to handle

        Returns:
            Message: Greeting message to send
        """
        # Get validation result first
        validation_result = component.validate({})
        if not validation_result.valid:
            raise FlowException(
                message="Failed to validate greeting",
                step="registration_attempt",
                action="validate",
                data={"validation": validation_result.error}
            )

        # Create greeting message
        content = component.to_message_content(validation_result.value)
        if not isinstance(content, str):
            raise FlowException(
                message="Invalid greeting content type",
                step="registration_attempt",
                action="format_content",
                data={"content_type": type(content).__name__}
            )

        message = Message(
            recipient=get_recipient(state_manager),
            content=TextContent(body=content)
        )

        # Just return the message - flow framework handles state
        return message

    @staticmethod
    def _handle_onboarding(state_manager: Any) -> tuple[bool, Dict]:
        """Handle onboarding attempt"""
        try:
            # Get registration data from state through proper accessor
            flow_data = state_manager.get_flow_state()
            if not flow_data or "data" not in flow_data:
                raise FlowException(
                    message="No registration data found",
                    step="registration_attempt",
                    action="get_data",
                    data={}
                )

            registration_data = flow_data["data"]

            # Get channel info through proper accessor method
            channel_id = state_manager.get_channel_id()
            if not channel_id:
                raise FlowException(
                    message="No channel identifier found",
                    step="registration_attempt",
                    action="get_channel",
                    data={}
                )

            member_data = {
                "firstname": registration_data.get("firstname"),
                "lastname": registration_data.get("lastname"),
                "phone": channel_id,
                "defaultDenom": "USD"  # Default denomination required by API
            }

            # Get properly initialized bot service
            from services.whatsapp.bot_service import get_bot_service
            bot_service = get_bot_service(state_manager)

            # Call onboardMember endpoint
            from core.api.auth import onboard_member
            success, auth_details = onboard_member(bot_service, member_data)

            if not success:
                return False, auth_details

            # State updates handled in onboard_member
            return True, auth_details

        except FlowException:
            # Flow errors stay in flows
            raise

        except Exception as e:
            # System errors propagate to top level
            logger.error(f"Error in registration handler: {str(e)}")
            raise SystemException(
                message=f"Error in registration flow: {str(e)}",
                code="FLOW_ERROR",
                service="member_flow",
                action="registration_attempt"
            )

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get registration step content with validation

        Args:
            step: Current step
            data: Optional step data

        Returns:
            Step content string

        Raises:
            FlowException: If step validation fails
        """
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("member_registration", step)

            # Get step content through registry
            component_type = FlowRegistry.get_step_component("member_registration", step)
            if component_type == "FirstNameInput":
                return "👤 What is your first name?"
            elif component_type == "LastNameInput":
                return "👤 What is your last name?"

            # Components handle their own messages
            return ""

        except FlowException as e:
            # Flow errors stay in flows
            logger.debug(f"Flow error in get_step_content: {str(e)}")
            raise FlowException(
                message=str(e),
                step=step,
                action="get_content",
                data={"error": str(e)}
            )

        except Exception as e:
            # System errors propagate to top level
            logger.error(f"System error in get_step_content: {str(e)}")
            raise SystemException(
                message=f"Error getting step content: {str(e)}",
                code="FLOW_ERROR",
                service="member_flow",
                action=f"get_content_{step}"
            )

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process registration step"""
        try:
            recipient = get_recipient(state_manager)

            # Get flow type from registry
            flow_type = "member_registration"

            # Process step
            if step == "welcome":
                # Get welcome component through registry
                component_type = FlowRegistry.get_step_component(flow_type, "welcome")
                welcome_component = create_component(component_type)

                if input_value:
                    # User clicked button, move to next step
                    next_step = FlowRegistry.get_next_step(flow_type, "welcome")

                    # Let flow framework handle progression and return next content
                    next_step_content = RegistrationFlow.get_step_content(next_step)
                    return Message(
                        recipient=recipient,
                        content=TextContent(body=next_step_content)
                    )

                # No input, show welcome message with button
                return welcome_component.get_message(recipient.channel_id.value)

            elif step == "firstname":
                # Get component through registry
                component_type = FlowRegistry.get_step_component(flow_type, "firstname")
                firstname_component = create_component(component_type)

                # Component handles validation and returns verified data
                verified_data = firstname_component.to_verified_data(input_value)

                # Store verified input data
                state_manager.update_flow_data(verified_data)

                # Let flow framework handle progression
                next_step = FlowRegistry.get_next_step(flow_type, "firstname")
                next_step_content = RegistrationFlow.get_step_content(next_step)
                return Message(
                    recipient=recipient,
                    content=TextContent(body=next_step_content)
                )

            elif step == "lastname":
                # Get component through registry
                component_type = FlowRegistry.get_step_component(flow_type, "lastname")
                lastname_component = create_component(component_type)

                # Component handles validation and returns verified data
                verified_data = lastname_component.to_verified_data(input_value)

                # Store verified input data
                state_manager.update_flow_data(verified_data)

                # Let flow framework handle progression
                next_step = FlowRegistry.get_next_step(flow_type, "lastname")
                next_step_content = RegistrationFlow.get_step_content(next_step)
                return Message(
                    recipient=recipient,
                    content=TextContent(body=next_step_content)
                )

            elif step == "registration_attempt":
                # Handle component based on type passed by framework
                if input_value == "Greeting":
                    try:
                        logger.info("Processing greeting component")
                        component = create_component(input_value)
                        return RegistrationFlow._handle_greeting(
                            messaging_service=messaging_service,
                            state_manager=state_manager,
                            component=component
                        )
                    except SystemException as e:
                        if "rate limit" in str(e).lower():
                            return Message(
                                recipient=get_recipient(state_manager),
                                content=TextContent(
                                    body="⚠️ Too many messages sent. Please wait a moment before trying again."
                                )
                            )
                        raise

                elif input_value == "OnBoardMember":
                    try:
                        logger.info("Processing registration")
                        success, auth_details = RegistrationFlow._handle_onboarding(state_manager)
                        if success:
                            logger.info("Registration successful, proceeding to dashboard")
                            # Let flow framework handle progression
                            next_step = FlowRegistry.get_next_step(flow_type, "registration_attempt")
                            next_step_content = RegistrationFlow.get_step_content(next_step)
                            return Message(
                                recipient=recipient,
                                content=TextContent(body=next_step_content)
                            )
                        else:
                            logger.info("Registration failed")
                            return Message(
                                recipient=get_recipient(state_manager),
                                content=TextContent(body=auth_details.get("message", "Registration failed"))
                            )
                    except SystemException:
                        raise

                else:
                    raise FlowException(
                        message=f"Invalid component type: {input_value}",
                        step="registration_attempt",
                        action="validate",
                        data={"component": input_value}
                    )

            elif step == "dashboard":
                # Get dashboard component through registry
                component_type = FlowRegistry.get_step_component("account_dashboard", "display")
                dashboard_component = create_component(component_type)
                dashboard_component.set_state_manager(state_manager)

                # Validate and get dashboard data
                validation_result = dashboard_component.validate({})
                if not validation_result.valid:
                    raise FlowException(
                        message=validation_result.error["message"],
                        step="dashboard",
                        action="validate_dashboard",
                        data={
                            "validation_error": validation_result.error,
                            "component": component_type
                        }
                    )

                # Get verified dashboard data with actions
                verified_data = dashboard_component.to_verified_data(validation_result.value)

                # Let flow framework handle progression
                next_step = FlowRegistry.get_next_step(flow_type, "dashboard")
                next_step_content = RegistrationFlow.get_step_content(next_step)
                return Message(
                    recipient=recipient,
                    content=TextContent(body=next_step_content)
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except ComponentException as e:
            # Component validation errors stay in components
            logger.debug(f"Component validation error: {str(e)}")
            raise FlowException(
                message=str(e),
                step=step,
                action="validate_component",
                data={"error": str(e)}
            )

        except FlowException:
            # Flow errors stay in flows but ensure they have step
            raise

        except Exception as e:
            # System errors propagate to top level
            logger.error(f"System error in registration flow: {str(e)}")
            raise SystemException(
                message=f"Error in registration flow: {str(e)}",
                code="FLOW_ERROR",
                service="member_flow",
                action=f"process_{step}"
            )
