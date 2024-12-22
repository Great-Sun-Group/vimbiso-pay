"""Menu and dashboard handling"""
import logging
from typing import Optional

from core.utils.flow_audit import FlowAuditLogger
from ...base_handler import BaseActionHandler
from ...types import WhatsAppMessage
from ..member.dashboard import DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class MenuHandler(BaseActionHandler):
    """Handler for menu and dashboard interactions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def show_dashboard(self, flow_type: str = "view", message: Optional[str] = None) -> WhatsAppMessage:
        """Display dashboard without flow processing"""
        try:
            # Initialize dashboard flow
            flow = DashboardFlow(flow_type=flow_type, success_message=message)
            flow.credex_service = self.service.credex_service
            flow.data = {"mobile_number": self.service.user.mobile_number}

            # Complete flow directly - this will handle state management
            return flow.complete()

        except Exception as e:
            logger.error(f"Dashboard display error: {str(e)}")
            audit.log_flow_event(
                "auth_handler",
                "dashboard_error",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "failure",
                str(e)
            )
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Failed to load dashboard. Please try again."
            )

    def handle_menu(self, message: Optional[str] = None, login: bool = False) -> WhatsAppMessage:
        """Display main menu"""
        try:
            # Handle login if needed
            if login:
                success, dashboard_data = self.service.auth_handler.auth_flow.attempt_login()
                if not success:
                    return self.service.auth_handler.auth_flow.handle_registration(register=True)

            # Show dashboard directly
            return self.show_dashboard(
                flow_type="login" if login else "view",
                message=message
            )

        except Exception as e:
            logger.error(f"Menu error: {str(e)}")
            audit.log_flow_event(
                "auth_handler",
                "menu_error",
                None,
                {"mobile_number": self.service.user.mobile_number},
                "failure",
                str(e)
            )
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Failed to load menu. Please try again."
            )

    def handle_hi(self) -> WhatsAppMessage:
        """Handle initial greeting"""
        audit.log_flow_event(
            "auth_handler",
            "greeting",
            None,
            {"mobile_number": self.service.user.mobile_number},
            "in_progress"
        )

        # Clear any existing flow state but initialize with proper structure
        current_state = self.service.user.state.state
        new_state = self.service.state_manager.prepare_state_update(
            current_state,
            flow_data={  # Initialize empty flow data structure
                "id": "user_state",
                "step": 0,
                "data": {
                    "mobile_number": self.service.user.mobile_number,
                    "flow_type": "auth",
                    "_validation_context": {},
                    "_validation_state": {}
                },
                "_previous_data": {}
            },
            mobile_number=self.service.user.mobile_number
        )

        # Log state transition
        audit.log_state_transition(
            "auth_handler",
            current_state,
            new_state,
            "success"
        )

        # Update state
        self.service.user.state.update_state(new_state, "greeting")

        return self.handle_menu(login=True)

    def handle_refresh(self) -> WhatsAppMessage:
        """Handle dashboard refresh"""
        audit.log_flow_event(
            "auth_handler",
            "refresh",
            None,
            {"mobile_number": self.service.user.mobile_number},
            "in_progress"
        )
        return self.handle_menu(message="Dashboard refreshed")
