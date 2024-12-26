"""Menu and dashboard handling"""
import logging
from typing import Optional

from core.utils.flow_audit import FlowAuditLogger
from ...base_handler import BaseActionHandler
from core.messaging.types import (
    Message,
    MessageRecipient,
    TextContent,
    ChannelIdentifier,
    ChannelType
)
from ..member.dashboard import DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class MenuHandler(BaseActionHandler):
    """Handler for menu and dashboard interactions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def show_dashboard(self, flow_type: str = "view", message: Optional[str] = None) -> Message:
        """Display dashboard without flow processing"""
        try:
            # Initialize dashboard flow
            flow = DashboardFlow(flow_type=flow_type, success_message=message)
            flow.credex_service = self.service.credex_service
            # Get member ID from state
            member_id = self.service.user.state.state.get("member_id")
            if not member_id:
                raise ValueError("Missing member ID")

            # Get channel identifier from state
            channel_id = self.service.user.channel_identifier

            flow.data = {
                "member_id": member_id,  # Primary identifier
                "channel": {  # Channel info at top level
                    "type": "whatsapp",
                    "identifier": channel_id
                }
            }

            # Complete flow directly - this will handle state management
            return flow.complete()

        except Exception as e:
            logger.error(f"Dashboard display error: {str(e)}")
            # Get member ID and channel identifier
            member_id = self.service.user.state.state.get("member_id")
            channel_id = self.service.user.channel_identifier

            # Log error with member and channel context
            audit.log_flow_event(
                "auth_handler",
                "dashboard_error",
                None,
                {
                    "member_id": member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id
                    }
                },
                "failure",
                str(e)
            )
            return Message(
                recipient=MessageRecipient(
                    member_id=member_id or "pending",
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=TextContent(
                    body="Failed to load dashboard. Please try again."
                )
            )

    def handle_menu(self, message: Optional[str] = None, login: bool = False) -> Message:
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
            # Get member ID and channel identifier
            member_id = self.service.user.state.state.get("member_id")
            channel_id = self.service.user.channel_identifier

            audit.log_flow_event(
                "auth_handler",
                "menu_error",
                None,
                {
                    "member_id": member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id
                    }
                },
                "failure",
                str(e)
            )
            return Message(
                recipient=MessageRecipient(
                    member_id=member_id or "pending",
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=TextContent(
                    body="Failed to load menu. Please try again."
                )
            )

    def handle_hi(self) -> Message:
        """Handle initial greeting"""
        audit.log_flow_event(
            "auth_handler",
            "greeting",
            None,
            {
                "channel": {
                    "type": "whatsapp",
                    "identifier": self.service.user.channel_identifier
                }
            },
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
                    "channel": {  # Channel info at top level
                        "type": "whatsapp",
                        "identifier": self.service.user.channel_identifier
                    },
                    "flow_type": "auth",
                    "_validation_context": {},
                    "_validation_state": {}
                },
                "_previous_data": {}
            },
            channel_identifier=self.service.user.channel_identifier
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

    def handle_refresh(self) -> Message:
        """Handle dashboard refresh"""
        audit.log_flow_event(
            "auth_handler",
            "refresh",
            None,
            {
                "channel": {
                    "type": "whatsapp",
                    "identifier": self.service.user.channel_identifier
                }
            },
            "in_progress"
        )
        return self.handle_menu(message="Dashboard refreshed")
