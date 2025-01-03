"""Authentication handlers using messaging service interface"""
import logging
from datetime import datetime
from typing import Any, Dict, Tuple

from core.messaging.flow import initialize_flow
from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException, SystemException

from ..utils import get_recipient

logger = logging.getLogger(__name__)


class AuthHandler:
    """Handler for authentication operations"""

    @staticmethod
    def attempt_login(messaging_service: MessagingServiceInterface, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Attempt to login user with channel ID

        Args:
            messaging_service: Service for sending messages
            state_manager: State manager instance

        Returns:
            Tuple[bool, Dict]: Success flag and response data
        """
        try:
            # Update state with auth attempt
            state_manager.update_state({
                "flow_data": {
                    "active_component": {
                        "type": "auth_handler",
                        "validation": {
                            "in_progress": True,
                            "attempts": state_manager.get_flow_data().get("auth_attempts", 0) + 1,
                            "last_attempt": datetime.utcnow().isoformat()
                        }
                    }
                }
            })

            # Get channel info through proper methods
            channel_type = state_manager.get_channel_type()
            channel_id = state_manager.get_channel_id()

            # Attempt login through messaging service
            response = messaging_service.authenticate_user(
                channel_type=channel_type,
                channel_id=channel_id
            )

            return True, response

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False, {"error": str(e)}

    @staticmethod
    def handle_greeting(messaging_service: MessagingServiceInterface, state_manager: Any) -> Message:
        """Handle initial greeting with login attempt

        Args:
            messaging_service: Service for sending messages
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
            success, response = AuthHandler.attempt_login(messaging_service, state_manager)

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
                return messaging_service.send_dashboard(
                    recipient=get_recipient(state_manager),
                    dashboard_data=dashboard
                )

            else:
                # Start registration for new users
                logger.info("User not found, starting registration")
                initialize_flow(state_manager, "registration")
                return messaging_service.send_text(
                    recipient=get_recipient(state_manager),
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
            return messaging_service.send_text(
                recipient=get_recipient(state_manager),
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
            return messaging_service.send_text(
                recipient=get_recipient(state_manager),
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
            return messaging_service.send_text(
                recipient=get_recipient(state_manager),
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
            return messaging_service.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error['message']}"
            )
