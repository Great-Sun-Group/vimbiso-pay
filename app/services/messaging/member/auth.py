"""Authentication handlers using messaging service interface"""
import logging
from typing import Any, Dict, Tuple

from core.messaging.flow import initialize_flow
from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException, SystemException

logger = logging.getLogger(__name__)


class AuthHandler:
    """Handler for authentication operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service

    def attempt_login(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Attempt to login user with channel ID

        Args:
            state_manager: State manager instance

        Returns:
            Tuple[bool, Dict]: Success flag and response data
        """
        try:
            # Get channel info
            channel = state_manager.get("channel")
            if not channel:
                raise ComponentException(
                    message="Channel information not found",
                    component="auth_handler",
                    field="channel",
                    value="None"
                )

            # Attempt login through messaging service
            response = self.messaging.authenticate_user(
                channel_type=channel["type"],
                channel_id=state_manager.get_channel_id()
            )

            return True, response

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False, {"error": str(e)}

    def handle_greeting(self, state_manager: Any) -> Message:
        """Handle initial greeting with login attempt

        Args:
            state_manager: State manager instance

        Returns:
            Message: Response message
        """
        try:
            # Validate state manager
            if not state_manager:
                raise ComponentException(
                    message="State manager is required",
                    component="auth_handler",
                    field="state_manager",
                    value="None"
                )

            # Attempt login
            success, response = self.attempt_login(state_manager)

            if success:
                # Extract data from response
                data = response.get("data", {})
                action = data.get("action", {})
                dashboard = data.get("dashboard", {})

                # Extract auth details
                auth_details = action.get("details", {})
                member_data = dashboard.get("member", {})
                accounts = dashboard.get("accounts", [])

                # Update auth state
                success, error = state_manager.update_state({
                    "member_id": auth_details.get("memberID"),
                    "jwt_token": auth_details.get("token"),
                    "authenticated": True,
                    "member_data": member_data,
                    "accounts": accounts,
                    "active_account_id": accounts[0]["accountID"] if accounts else None
                })
                if not success:
                    raise FlowException(
                        message=f"Failed to update auth state: {error}",
                        step="login",
                        action="update_auth",
                        data={"error": error}
                    )

                # Update flow state
                success, error = state_manager.update_state({
                    "flow_data": {
                        "flow_type": "dashboard",
                        "step": 0,
                        "current_step": "main",
                        "type": "dashboard_display",
                        "data": {
                            "member_id": auth_details.get("memberID")
                        }
                    }
                })
                if not success:
                    raise FlowException(
                        message=f"Failed to update flow state: {error}",
                        step="login",
                        action="update_flow",
                        data={"error": error}
                    )

                # Send dashboard message
                logger.info("Login successful, showing dashboard")
                return self.messaging.send_dashboard(
                    recipient=MessageRecipient(
                        channel_id=state_manager.get_channel_id(),
                        member_id=auth_details.get("memberID")
                    ),
                    dashboard_data=dashboard
                )

            else:
                # Start registration for new users
                logger.info("User not found, starting registration")
                initialize_flow(state_manager, "registration")
                return self.messaging.send_text(
                    recipient=MessageRecipient(
                        channel_id=state_manager.get_channel_id()
                    ),
                    text="👋 Welcome to VimbisoPay! Let's get you registered."
                )

        except ComponentException as e:
            # Handle component validation errors
            logger.error("Auth validation error", extra={
                "component": e.component,
                "field": e.field,
                "value": e.value
            })
            error = ErrorHandler.handle_component_error(
                component=e.component,
                field=e.field,
                value=e.value,
                message=str(e)
            )
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id()
                ),
                text=f"❌ {error['message']}"
            )

        except FlowException as e:
            # Handle flow errors
            logger.error("Auth flow error", extra={
                "step": e.step,
                "action": e.action,
                "data": e.data
            })
            error = ErrorHandler.handle_flow_error(
                step=e.step,
                action=e.action,
                data=e.data,
                message=str(e)
            )
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id()
                ),
                text=f"❌ {error['message']}"
            )

        except SystemException as e:
            # Handle system errors
            logger.error("Auth system error", extra={
                "code": e.code,
                "service": e.service,
                "action": e.action
            })
            error = ErrorHandler.handle_system_error(
                code=e.code,
                service=e.service,
                action=e.action,
                message=str(e)
            )
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id()
                ),
                text=f"❌ {error['message']}"
            )

        except Exception as e:
            # Handle unexpected errors
            logger.error("Unexpected auth error", extra={"error": str(e)})
            error = ErrorHandler.handle_system_error(
                code="AUTH_ERROR",
                service="auth_handler",
                action="handle_greeting",
                message="An unexpected error occurred"
            )
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id()
                ),
                text=f"❌ {error['message']}"
            )
