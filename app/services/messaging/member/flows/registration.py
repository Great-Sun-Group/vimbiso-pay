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

    # Flow configuration from registry
    FLOW_TYPE = "member_registration"
    HANDLER_TYPE = "member"

    @staticmethod
    def _handle_greeting(messaging_service: MessagingServiceInterface, state_manager: Any, component: Any, current_index: int, components: list) -> Message:
        """Handle greeting component"""
        try:
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

        except FlowException:
            raise
        except Exception as e:
            raise FlowException(
                message=f"Error handling greeting: {str(e)}",
                step="registration_attempt",
                action="handle_greeting",
                data={"error": str(e)}
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
            FlowRegistry.validate_flow_step(RegistrationFlow.FLOW_TYPE, step)

            # Get step content
            if step == "firstname":
                return "👤 What is your first name?"
            elif step == "lastname":
                return "👤 What is your last name?"
            # No default step content needed - components handle their own messages

            # Empty string for unknown steps (should be caught by validation)
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

            # Process step
            if step == "welcome":
                # Get welcome component
                welcome_component = create_component("RegistrationWelcome")

                if input_value:
                    # Component handles validation - will raise exception if invalid
                    welcome_component.to_verified_data(input_value)

                    # Get next step
                    next_step = FlowRegistry.get_next_step(RegistrationFlow.FLOW_TYPE, "welcome")

                    # Update flow progression
                    state_manager.update_flow_state(
                        flow_type=RegistrationFlow.FLOW_TYPE,
                        step=next_step,
                        data={
                            "active_component": {
                                "type": "FirstNameInput",
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

                # If no input, return welcome message
                validation_result = welcome_component.validate({})
                if not validation_result.valid:
                    raise FlowException(
                        message=validation_result.error["message"],
                        step="welcome",
                        action="validate_welcome",
                        data={"validation": validation_result.error}
                    )

                content = welcome_component.to_message_content(validation_result.value)
                return Message(
                    recipient=recipient,
                    content=TextContent(body=content)
                )

            elif step == "firstname":
                # Get firstname component
                firstname_component = create_component("FirstNameInput")

                # Component handles validation and returns verified data
                verified_data = firstname_component.to_verified_data(input_value)

                # Store verified input data
                state_manager.update_flow_data(verified_data)

                # Get next step and update flow progression
                next_step = FlowRegistry.get_next_step(RegistrationFlow.FLOW_TYPE, "firstname")

                # Update flow progression
                state_manager.update_flow_state(
                    flow_type=RegistrationFlow.FLOW_TYPE,
                    step=next_step,
                    data={
                        "active_component": {
                            "type": "LastNameInput",
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
                # Get lastname component
                lastname_component = create_component("LastNameInput")

                # Component handles validation and returns verified data
                verified_data = lastname_component.to_verified_data(input_value)

                # Store verified input data
                state_manager.update_flow_data(verified_data)

                # Move to registration attempt step
                next_step = FlowRegistry.get_next_step(RegistrationFlow.FLOW_TYPE, "lastname")
                state_manager.update_flow_state(
                    flow_type=RegistrationFlow.FLOW_TYPE,
                    step=next_step,
                    data={
                        "active_component": {
                            "type": "Greeting",
                            "components": ["Greeting", "OnBoardMember"],
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
                # Get current component from state
                flow_data = state_manager.get_flow_state() or {}
                active_component = flow_data.get("data", {}).get("active_component", {})
                component_type = active_component.get("type")
                components = active_component.get("components", [])
                component_index = active_component.get("component_index", 0)

                if component_type == "Greeting":
                    # Handle greeting component
                    greeting_component = create_component("Greeting")
                    greeting_message = RegistrationFlow._handle_greeting(
                        messaging_service=messaging_service,
                        state_manager=state_manager,
                        component=greeting_component,
                        current_index=component_index,
                        components=components
                    )

                    # Send greeting through messaging service
                    messaging_service.send_message(greeting_message)

                    # Let flow progress to next component (OnBoardMember)
                    return RegistrationFlow.process_step(
                        messaging_service=messaging_service,
                        state_manager=state_manager,
                        step=step,
                        input_value=None
                    )

                elif component_type == "OnBoardMember":
                    # Handle onboarding
                    onboard_component = create_component("OnBoardMember")
                    onboard_component.set_state_manager(state_manager)
                    # Get properly initialized bot service
                    from services.whatsapp.bot_service import get_bot_service
                    bot_service = get_bot_service(state_manager)
                    onboard_component.set_bot_service(bot_service)

                    # Process onboarding
                    validation_result = onboard_component.validate(None)
                    if not validation_result.valid:
                        raise FlowException(
                            message=validation_result.error.get("message", "Validation failed"),
                            step="registration_attempt",
                            action="validate_onboarding",
                            data={"validation": validation_result.error}
                        )

                    # Update state with verified data
                    state_manager.update_flow_data(onboard_component.to_verified_data(validation_result.value))

                    # Move to dashboard step
                    next_step = FlowRegistry.get_next_step(RegistrationFlow.FLOW_TYPE, "registration_attempt")
                    state_manager.update_flow_state(
                        flow_type=RegistrationFlow.FLOW_TYPE,
                        step=next_step,
                        data={
                            "active_component": {
                                "type": "AccountDashboard",
                                "validation": {
                                    "in_progress": False,
                                    "attempts": 0,
                                    "last_attempt": None
                                }
                            }
                        }
                    )

                    # Let flow progress to dashboard step
                    return RegistrationFlow.process_step(
                        messaging_service=messaging_service,
                        state_manager=state_manager,
                        step=next_step,
                        input_value=None
                    )

                else:
                    raise FlowException(
                        message=f"Invalid component type: {component_type}",
                        step="registration_attempt",
                        action="validate",
                        data={"component": component_type}
                    )

            elif step == "dashboard":
                # Get dashboard component
                dashboard_component = create_component("AccountDashboard")
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
                            "component": "account_dashboard"
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
                        action="validate_dashboard",
                        data={
                            "validation_error": validation_result.error,
                            "component": "account_dashboard"
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
