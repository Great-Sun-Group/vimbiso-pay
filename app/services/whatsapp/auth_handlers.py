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
        """Handle registration flow"""
        try:
            if register:
                return WhatsAppMessage.create_button(
                    to=self.service.user.mobile_number,
                    text=REGISTER,
                    buttons=[{
                        "id": "start_registration",
                        "title": "Introduce yourself"
                    }]
                )

            return self.handle_action_menu()

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Registration failed. Please try again."
            )

    def _attempt_login(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Attempt login and store JWT token"""
        try:
            # Attempt login
            success, response = self.service.credex_service._auth.login(
                self.service.user.mobile_number
            )

            if not success:
                if any(
                    phrase in response.lower()
                    for phrase in ["new user", "new here", "member not found"]
                ):
                    return False, None
                logger.error(f"Login failed: {response}")
                return False, None

            # Extract JWT token and dashboard data
            jwt_token = self.service.credex_service._auth._jwt_token
            if not jwt_token:
                return False, None

            dashboard_data = response.get("data", {})
            logger.info(f"Dashboard data from login: {dashboard_data}")

            # Update state
            self.service.user.state.update_state({
                "jwt_token": jwt_token,
                "authenticated": True,
                "profile": dashboard_data
            }, "login_success")

            # Propagate token
            self.service.credex_service.jwt_token = jwt_token
            return True, dashboard_data

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False, None

    def handle_action_menu(self, message: Optional[str] = None, login: bool = False) -> WhatsAppMessage:
        """Display main menu"""
        try:
            # Handle login if needed
            if login:
                success, dashboard_data = self._attempt_login()
                if not success:
                    return self.handle_action_register(register=True)

            # Initialize dashboard flow
            flow = DashboardFlow(
                flow_type="login" if login else "view",
                message=message
            )

            # Set up credex service
            credex_service = CredExService(user=self.service.user)
            credex_service._parent_service = self.service

            # Propagate JWT token
            if jwt_token := self.service.user.state.jwt_token:
                logger.info("Propagating JWT token")
                credex_service.jwt_token = jwt_token

            # Configure flow
            flow.credex_service = credex_service
            flow.data = {
                "mobile_number": self.service.user.mobile_number
            }

            # Complete flow
            return flow.complete()

        except Exception as e:
            logger.error(f"Menu error: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Failed to load menu. Please try again."
            )

    def handle_hi(self) -> WhatsAppMessage:
        """Handle initial greeting"""
        return self.handle_action_menu(login=True)

    def handle_refresh(self) -> WhatsAppMessage:
        """Handle dashboard refresh"""
        return self.handle_action_menu(message="Dashboard refreshed")
