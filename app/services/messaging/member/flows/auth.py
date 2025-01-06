"""Authentication flow implementation"""
import logging
from typing import Any, Dict, Optional

from core.api.auth_client import get_login_response_data, login
from core.api.profile import update_profile_from_response
from core.components.registry import create_component
from core.messaging.formatters import AccountFormatters
from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import Button, Message, TextContent
from core.utils.exceptions import FlowException, SystemException

from ...utils import get_recipient
from ..constants import REGISTRATION_NEEDED

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
    def _handle_greeting(messaging_service: MessagingServiceInterface, state_manager: Any, component: Any, current_index: int, components: list) -> Message:
        """Handle greeting component"""
        # Get validation result first
        validation_result = component.validate({})
        if not validation_result.valid:
            raise FlowException(
                message="Failed to validate greeting",
                step="login",
                action="validate",
                data={"validation": validation_result.error}
            )

        # Create greeting message
        content = component.to_message_content(validation_result.value)
        if not isinstance(content, str):
            raise FlowException(
                message="Invalid greeting content type",
                step="login",
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
                "flow_type": "member_auth",
                "step": "login",
                "step_index": 0,
                "total_steps": 2,
                "active_component": component_state
            }
        })

        # Mark component as completed
        component.validation_state.update({
            "in_progress": False,
            "completed": True,
            "error": None
        })

        # Get current flow state
        flow_state = state_manager.get_flow_state()
        if not flow_state:
            raise FlowException(
                message="Lost flow state",
                step="login",
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
    def _handle_login(state_manager: Any) -> tuple[bool, Dict]:
        """Handle login attempt"""
        # Attempt login
        success, auth_details = login(state_manager.get_channel_id())

        # Handle login result
        if success and auth_details:
            # Validate auth details
            if not auth_details.get("token") or not auth_details.get("memberID"):
                raise FlowException(
                    message="Invalid auth details",
                    step="login",
                    action="validate_auth",
                    data={"auth": auth_details}
                )

            # Get full response data for state update
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

            return True, auth_details
        else:
            return False, auth_details

    @staticmethod
    def _handle_dashboard(messaging_service: MessagingServiceInterface, state_manager: Any, verified_data: Dict) -> Message:
        """Handle dashboard display"""
        # Format message using account data
        active_account = verified_data["active_account"]
        balance_data = active_account.get("balanceData", {})

        # Get member tier from dashboard data
        member_data = verified_data["dashboard"].get("member", {})
        member_tier = member_data.get("memberTier")
        tier_limit_display = ""
        if member_tier < 2:
            remaining_usd = balance_data.get("remainingAvailableUSD", "0.00")
            tier_limit_display = f"\n\n⏳ DAILY MEMBER TIER LIMIT: {remaining_usd} USD"

        account_data = {
            "accountName": active_account.get("accountName"),
            "accountHandle": active_account.get("accountHandle"),
            **balance_data,
            "tier_limit_display": tier_limit_display
        }
        message = AccountFormatters.format_dashboard(account_data)

        # Get recipient for message
        recipient = get_recipient(state_manager)

        # Check if we should use list format
        if verified_data.get("use_list"):
            # Use WhatsApp's list message format
            return messaging_service.send_interactive(
                recipient=recipient,
                body=message,
                sections=verified_data["sections"],
                button_text=verified_data.get("button_text", "Select Option")
            )
        else:
            # Check if buttons are provided
            if "buttons" in verified_data:
                # Convert button dictionaries to Button objects (max 3 for WhatsApp)
                buttons = [
                    Button(id=btn["id"], title=btn["title"])
                    for btn in verified_data["buttons"][:3]  # Limit to first 3 buttons
                ]
                # Use button format for simple yes/no interactions
                return messaging_service.send_interactive(
                    recipient=recipient,
                    body=message,
                    buttons=buttons
                )
            else:
                # Fallback to simple text message
                return Message(
                    recipient=recipient,
                    content=TextContent(body=message)
                )

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process auth step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("member_auth", step)

            if step == "login":
                # Get components for this step
                components = FlowRegistry.get_step_component("member_auth", "login")
                if not isinstance(components, list):
                    components = [components]

                # Get current component info from state
                flow_state = state_manager.get_flow_state()
                if not flow_state:
                    raise FlowException(
                        message="No active flow state",
                        step="login",
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
                        logger.info("Starting greeting sequence")

                        # Get and send greeting message
                        greeting_message = AuthFlow._handle_greeting(
                            messaging_service=messaging_service,
                            state_manager=state_manager,
                            component=component,
                            current_index=current_index,
                            components=components
                        )

                        # Send greeting through messaging service
                        messaging_service.send_message(greeting_message)

                        # Proceed to login handler
                        success, auth_details = AuthFlow._handle_login(state_manager)
                        if success:
                            # Continue to login complete step
                            return AuthFlow.process_step(
                                messaging_service=messaging_service,
                                state_manager=state_manager,
                                step="login_complete",
                                input_value=input_value
                            )
                        else:
                            # Signal that registration is needed
                            return REGISTRATION_NEEDED

                    except SystemException as e:
                        if "rate limit" in str(e).lower():
                            # Return error message for rate limit
                            return Message(
                                recipient=get_recipient(state_manager),
                                content=TextContent(
                                    body="⚠️ Too many messages sent. Please wait a moment before trying again."
                                )
                            )
                        raise
                elif current_type == "LoginHandler":
                    try:
                        success, auth_details = AuthFlow._handle_login(state_manager)
                        if success:
                            # Continue to login complete step
                            return AuthFlow.process_step(
                                messaging_service=messaging_service,
                                state_manager=state_manager,
                                step="login_complete",
                                input_value=input_value
                            )
                        else:
                            # Signal that registration is needed
                            return REGISTRATION_NEEDED

                    except SystemException:
                        # Let system exceptions propagate up
                        raise
                    except Exception as e:
                        # Wrap other errors
                        raise SystemException(
                            message=f"Error in login handler: {str(e)}",
                            code="LOGIN_ERROR",
                            service="auth_flow",
                            action="login"
                        )

            elif step == "login_complete":
                # Get dashboard component through account handler
                component_type = FlowRegistry.get_step_component("account_dashboard", "display")
                component = create_component(component_type)
                component.set_state_manager(state_manager)

                # Validate and get dashboard data
                validation_result = component.validate({})
                if not validation_result.valid:
                    raise FlowException(
                        message=validation_result.error["message"],
                        step="login_complete",
                        action="validate_dashboard",
                        data={
                            "validation_error": validation_result.error,
                            "component": "account_dashboard"
                        }
                    )

                # Get verified dashboard data with actions
                verified_data = component.to_verified_data(validation_result.value)

                # Handle dashboard display
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

        except FlowException:
            raise

        except Exception as e:
            raise SystemException(
                message=f"Error in auth flow: {str(e)}",
                code="FLOW_ERROR",
                service="auth_flow",
                action=f"process_{step}"
            )
