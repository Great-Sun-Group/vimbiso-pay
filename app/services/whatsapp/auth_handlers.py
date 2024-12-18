"""Authentication and menu handlers"""
import logging
from typing import Optional, Tuple, Dict, Any

from .base_handler import BaseActionHandler
from .screens import REGISTER
from .types import WhatsAppMessage
from .handlers.member.dashboard import DashboardFlow
from services.credex.service import CredExService

logger = logging.getLogger(__name__)


class AuthActionHandler(BaseActionHandler):
    """Handler for authentication and menu-related actions"""

    def handle_action_register(self, register: bool = False) -> WhatsAppMessage:
        """Redirect to member registration flow"""
        try:
            if register:
                # No need to set flow data here - will be set by _start_flow
                return {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": self.service.user.mobile_number,
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": REGISTER
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {
                                        "id": "start_registration",
                                        "title": "Introduce yourself"
                                    }
                                }
                            ]
                        }
                    }
                }

            return self.handle_action_menu()

        except Exception as e:
            logger.error(f"Error in registration: {str(e)}")
            return self.get_response_template("Registration failed. Please try again.")

    def _attempt_login(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Attempt login and store JWT token. Returns (success, dashboard_data)"""
        try:
            # Try login - this should return dashboard data in the response
            success, response = self.service.credex_service._auth.login(
                self.service.user.mobile_number
            )
            if not success:
                if any(phrase in response.lower() for phrase in ["new user", "new here", "member not found"]):
                    return False, None
                logger.error(f"Login failed: {response}")
                return False, None

            # Log the full login response for debugging
            logger.info(f"Login response: {response}")

            # Store JWT token through user's state and propagate to all services
            jwt_token = self.service.credex_service._auth._jwt_token
            if jwt_token:
                # Get the dashboard data from the response
                dashboard_data = response.get("data", {})
                logger.info(f"Dashboard data from login: {dashboard_data}")

                # Update state with token and profile data
                self.service.user.state.update_state({
                    "jwt_token": jwt_token,
                    "authenticated": True,
                    "profile": dashboard_data  # Store dashboard data from login response
                }, "login_success")

                # Log the updated state for debugging
                logger.info(f"Updated state after login: {self.service.user.state.state}")

                # Use property setter to properly propagate token
                self.service.credex_service.jwt_token = jwt_token
                return True, dashboard_data

            return False, None

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False, None

    def handle_action_menu(self, message: Optional[str] = None, login: bool = False) -> WhatsAppMessage:
        """Display main menu"""
        try:
            # Attempt login if needed
            if login:
                success, dashboard_data = self._attempt_login()
                if not success:
                    return self.handle_action_register(register=True)

            # Initialize dashboard flow to display current state
            flow = DashboardFlow(
                flow_type="login" if login else "view",
                message=message
            )

            # Create a new CredExService instance with proper parent relationship
            credex_service = CredExService(user=self.service.user)
            credex_service._parent_service = self.service

            # Propagate JWT token from state if available
            jwt_token = self.service.user.state.jwt_token
            if jwt_token:
                logger.info("Propagating JWT token to new CredExService instance")
                credex_service.jwt_token = jwt_token

            # Set the service on the flow
            flow.credex_service = credex_service
            flow.data = {
                "mobile_number": self.service.user.mobile_number
            }

            # Complete flow and return dashboard display
            return flow.complete()

        except Exception as e:
            logger.error(f"Menu error: {str(e)}")
            return self.get_response_template("Failed to load menu. Please try again.")

    def handle_hi(self) -> WhatsAppMessage:
        """Handle initial greeting"""
        return self.handle_action_menu(login=True)

    def handle_refresh(self) -> WhatsAppMessage:
        """Handle dashboard refresh request"""
        return self.handle_action_menu(message="Dashboard refreshed")
