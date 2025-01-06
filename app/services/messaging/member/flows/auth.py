"""Authentication flow implementation"""
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from core.api.auth_client import login, get_login_response_data
from core.api.profile import update_profile_from_response
from core.components.registry import create_component
from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import Message, TextContent, Button
from core.messaging.formatters import AccountFormatters
from core.utils.exceptions import FlowException, SystemException

from ...utils import get_recipient

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
        # Send greeting message
        content = component.to_message_content(component.validate({}).value)
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

        # Initialize flow state with proper structure
        now = datetime.utcnow().isoformat()
        state_manager.update_state({
            "flow_data": {
                "flow_type": "member_auth",
                "step": "login",
                "step_index": 0,
                "total_steps": 2,
                "active_component": {
                    "type": "greeting",
                    "component_index": 0,
                    "validation": {
                        "in_progress": True,
                        "attempts": 0,
                        "last_attempt": now
                    }
                },
                "validation": {
                    "in_progress": True,
                    "attempts": 0,
                    "last_attempt": now,
                    "operation": "greeting_start"
                }
            }
        })

        # Send greeting and wait for response
        greeting_response = messaging_service.send_message(message)
        if not greeting_response:
            now = datetime.utcnow().isoformat()
            state_manager.update_state({
                "flow_data": {
                    "flow_type": "member_auth",
                    "step": "login",
                    "step_index": 0,
                    "total_steps": 2,
                    "active_component": {
                        "type": "greeting",
                        "component_index": 0,
                        "validation": {
                            "in_progress": False,
                            "completed": False,
                            "error": {
                                "message": "Failed to send greeting",
                                "timestamp": now
                            },
                            "attempts": 1,
                            "last_attempt": now
                        }
                    },
                    "validation": {
                        "in_progress": False,
                        "completed": False,
                        "error": {
                            "message": "Failed to send greeting",
                            "timestamp": now
                        },
                        "attempts": 1,
                        "last_attempt": now,
                        "operation": "greeting_failed"
                    }
                }
            })
            raise FlowException(
                message="Failed to send greeting",
                step="login",
                action="send_greeting",
                data={}
            )

        # Verify WhatsApp accepted the message
        if not greeting_response.metadata or not greeting_response.metadata.get("whatsapp_message_id"):
            logger.error("WhatsApp did not accept greeting message")
            now = datetime.utcnow().isoformat()
            state_manager.update_state({
                "flow_data": {
                    "flow_type": "member_auth",
                    "step": "login",
                    "step_index": 0,
                    "total_steps": 2,
                    "active_component": {
                        "type": "greeting",
                        "component_index": 0,
                        "validation": {
                            "in_progress": False,
                            "completed": False,
                            "error": {
                                "message": "WhatsApp did not accept greeting",
                                "timestamp": now
                            },
                            "attempts": 1,
                            "last_attempt": now
                        }
                    },
                    "validation": {
                        "in_progress": False,
                        "completed": False,
                        "error": {
                            "message": "WhatsApp did not accept greeting",
                            "timestamp": now
                        },
                        "attempts": 1,
                        "last_attempt": now,
                        "operation": "greeting_acceptance_failed"
                    }
                }
            })
            raise FlowException(
                message="WhatsApp did not accept greeting",
                step="login",
                action="verify_acceptance",
                data={"response": greeting_response}
            )

        # Update state with completed validation and consistent structure
        now = datetime.utcnow().isoformat()
        state_manager.update_state({
            "flow_data": {
                "flow_type": "member_auth",  # Maintain consistent flow type
                "active_component": {
                    "type": "greeting",  # Keep current component type
                    "component_index": current_index + 1,  # Advance index
                    "next_type": components[current_index + 1],  # Track next component
                    "validation": {
                        "in_progress": False,
                        "completed": True,
                        "attempts": 1,
                        "last_attempt": now
                    }
                },
                "step": "login",
                "step_index": 0,
                "total_steps": 2,
                "validation": {
                    "in_progress": False,
                    "completed": True,
                    "attempts": 1,
                    "last_attempt": now,
                    "operation": "greeting_complete"
                },
                "data": {  # Include data field for consistency
                    "updated_at": now
                }
            }
        })

        # Log successful acceptance
        logger.info("Greeting accepted by WhatsApp with ID: %s",
                    greeting_response.metadata.get("whatsapp_message_id") if greeting_response.metadata else "No message ID")

        return greeting_response

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
            tier_limit_display = f"\n⏳ DAILY MEMBER TIER LIMIT: {remaining_usd} USD"

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

                # Create and validate current component
                component = create_component(current_type)
                validation = component.validate({})  # Both components take empty dict
                if not validation.valid:
                    raise FlowException(
                        message=f"Failed to validate {current_type}",
                        step="login",
                        action="validate",
                        data={"validation": validation.error}
                    )

                # Handle component based on type
                if current_type == "Greeting":
                    try:
                        logger.info("Starting greeting sequence")

                        # Handle greeting and wait for confirmation
                        greeting_response = AuthFlow._handle_greeting(
                            messaging_service=messaging_service,
                            state_manager=state_manager,
                            component=component,
                            current_index=current_index,
                            components=components
                        )

                        logger.info("Greeting sent with content: %s",
                                    greeting_response.content.body if greeting_response and greeting_response.content else "None")
                        logger.info("Verifying completion")

                        # Get updated flow state after greeting
                        flow_state = state_manager.get_flow_state()
                        logger.debug("Flow state after greeting: %s", flow_state)
                        if not flow_state:
                            raise FlowException(
                                message="Lost flow state after greeting",
                                step="login",
                                action="verify_state",
                                data={}
                            )

                        # Verify greeting was completed
                        component_state = flow_state.get("active_component", {})
                        if not component_state.get("validation", {}).get("completed"):
                            raise FlowException(
                                message="Greeting was not completed",
                                step="login",
                                action="verify_completion",
                                data={"component_state": component_state}
                            )

                        # Verify WhatsApp accepted the message
                        if not greeting_response.metadata or not greeting_response.metadata.get("whatsapp_message_id"):
                            logger.error("WhatsApp did not accept greeting message")
                            raise FlowException(
                                message="WhatsApp did not accept greeting",
                                step="login",
                                action="verify_acceptance",
                                data={"response": greeting_response}
                            )

                        logger.info("Greeting accepted by WhatsApp, proceeding to login")

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
                                # Return registration message
                                recipient = get_recipient(state_manager)
                                message_content = auth_details.get("message") if auth_details else "Login failed"
                                if not isinstance(message_content, str):
                                    raise FlowException(
                                        message="Invalid message content type",
                                        step="login",
                                        action="format_content",
                                        data={"content_type": type(message_content).__name__}
                                    )

                                return Message(
                                    recipient=recipient,
                                    content=TextContent(body=message_content)
                                )

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
