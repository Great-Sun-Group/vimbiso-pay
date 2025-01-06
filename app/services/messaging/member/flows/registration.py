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
from .auth import AuthFlow

logger = logging.getLogger(__name__)


class RegistrationFlow:
    """Member registration flow"""

    @staticmethod
    def _handle_greeting(messaging_service: MessagingServiceInterface, state_manager: Any, component: Any, current_index: int, components: list) -> Message:
        """Handle greeting component"""
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

        # Get component state
        component_state = component.get_ui_state()

        # Initialize flow state
        state_manager.update_state({
            "flow_data": {
                "flow_type": "member_registration",
                "step": "registration_attempt",
                "step_index": 0,
                "total_steps": 3,  # welcome, registration, dashboard
                "active_component": component_state
            }
        })

        # Mark component as completed
        component_state["validation"].update({
            "in_progress": False,
            "completed": True,
            "error": None
        })

        # Get current flow state
        flow_state = state_manager.get_flow_state()
        if not flow_state:
            raise FlowException(
                message="Lost flow state",
                step="registration_attempt",
                action="update_state",
                data={}
            )

        # Advance to next component while preserving flow state
        next_component = components[current_index + 1]
        flow_state.update({
            "active_component": {
                "type": next_component,
                "component_index": current_index + 1,
                "validation": {
                    "in_progress": False,
                    "completed": False,
                    "attempts": 0
                }
            }
        })

        # Update state preserving structure
        state_manager.update_state({
            "flow_data": flow_state
        })

        # Return greeting message to be sent through proper path
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

                    # Get next component through registry
                    next_component = FlowRegistry.get_step_component(flow_type, next_step)

                    # Update flow progression
                    state_manager.update_flow_state(
                        flow_type=flow_type,
                        step=next_step,
                        data={
                            "active_component": {
                                "type": next_component,
                                "validation": {
                                    "in_progress": False,
                                    "attempts": 0,
                                    "last_attempt": None
                                }
                            }
                        }
                    )

                    # Return next step content
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

                # Get next step and component through registry
                next_step = FlowRegistry.get_next_step(flow_type, "firstname")
                next_component = FlowRegistry.get_step_component(flow_type, next_step)

                # Update flow progression
                state_manager.update_flow_state(
                    flow_type=flow_type,
                    step=next_step,
                    data={
                        "active_component": {
                            "type": next_component,
                            "validation": {
                                "in_progress": False,
                                "attempts": 0,
                                "last_attempt": None
                            }
                        }
                    }
                )

                # Return next step content
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

                # Get next step and components through registry
                next_step = FlowRegistry.get_next_step(flow_type, "lastname")
                next_components = FlowRegistry.get_step_component(flow_type, next_step)
                if not isinstance(next_components, list):
                    next_components = [next_components]

                # Update flow progression
                state_manager.update_flow_state(
                    flow_type=flow_type,
                    step=next_step,
                    data={
                        "active_component": {
                            "type": next_components[0],
                            "components": next_components,
                            "component_index": 0,
                            "validation": {
                                "in_progress": False,
                                "attempts": 0,
                                "last_attempt": None
                            }
                        }
                    }
                )

                # Let flow progress to registration attempt step
                return RegistrationFlow.process_step(
                    messaging_service=messaging_service,
                    state_manager=state_manager,
                    step=next_step,
                    input_value=None
                )

            elif step == "registration_attempt":
                # Get components for this step
                components = FlowRegistry.get_step_component("member_registration", "registration_attempt")
                if not isinstance(components, list):
                    components = [components]

                # Get current component info from state
                flow_state = state_manager.get_flow_state()
                if not flow_state:
                    raise FlowException(
                        message="No active flow state",
                        step="registration_attempt",
                        action="process",
                        data={}
                    )

                component_state = flow_state.get("active_component", {})
                current_index = component_state.get("component_index", 0)
                current_type = components[current_index]

                # Create component
                component = create_component(current_type)

                # Handle component based on type
                if current_type == "Greeting":
                    try:
                        logger.info("Starting registration greeting sequence")

                        # Get and send greeting message
                        greeting_message = RegistrationFlow._handle_greeting(
                            messaging_service=messaging_service,
                            state_manager=state_manager,
                            component=component,
                            current_index=current_index,
                            components=components
                        )

                        # Send greeting through messaging service
                        messaging_service.send_message(greeting_message)

                        # Proceed to onboard member handler
                        success, auth_details = RegistrationFlow._handle_onboarding(state_manager)
                        if success:
                            # Continue to dashboard step
                            return RegistrationFlow.process_step(
                                messaging_service=messaging_service,
                                state_manager=state_manager,
                                step="dashboard",
                                input_value=None
                            )
                        else:
                            # Registration failed
                            return Message(
                                recipient=get_recipient(state_manager),
                                content=TextContent(body=auth_details.get("message", "Registration failed"))
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

                else:
                    raise FlowException(
                        message=f"Invalid component type: {current_type}",
                        step="registration_attempt",
                        action="validate",
                        data={"component": current_type}
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

                # Handle dashboard display using auth flow formatter
                return AuthFlow._handle_dashboard(
                    messaging_service=messaging_service,
                    state_manager=state_manager,
                    verified_data=verified_data
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
