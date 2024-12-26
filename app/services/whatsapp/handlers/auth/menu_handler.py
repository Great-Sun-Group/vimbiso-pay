"""Menu and dashboard handling"""
import logging
from typing import Optional

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.flow_audit import FlowAuditLogger

from ...base_handler import BaseActionHandler
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
            # Get current state
            current_state = self.service.user.state.state
            if not current_state:
                raise ValueError("No state found")

            # Log current state for debugging
            logger.debug(f"Current state before dashboard: {current_state}")

            # Initialize dashboard flow
            flow = DashboardFlow(flow_type=flow_type, success_message=message)

            # Set services
            flow.credex_service = self.service.credex_service
            flow.credex_service._parent_service = self.service

            # Get member ID and channel info from state
            member_id = current_state.get("member_id")
            if not member_id:
                raise ValueError("Missing member ID")

            channel_id = current_state.get("channel", {}).get("identifier")
            if not channel_id:
                channel_id = self.service.user.channel_identifier

            # Set flow data with proper structure
            flow.data = {
                "member_id": member_id,
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                },
                "profile": current_state.get("profile", {}),
                "account_id": current_state.get("account_id"),
                "authenticated": current_state.get("authenticated", False),
                "jwt_token": current_state.get("jwt_token")
            }

            # Log flow data for debugging
            logger.debug(f"Flow data before complete: {flow.data}")

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
                # Only show dashboard if login was successful
                return self.show_dashboard(
                    flow_type="login",
                    message=message
                )

            # Only show dashboard for non-login menu if we have a member_id
            if not self.service.user.state.state.get("member_id"):
                return self.service.auth_handler.auth_flow.handle_registration(register=True)

            return self.show_dashboard(
                flow_type="view",
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
        # Get current state
        current_state = self.service.user.state.state or {}

        # Log initial state for debugging
        logger.debug(f"Initial state in handle_hi: {current_state}")

        # Log greeting event
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

        # Prepare new state with proper structure
        new_state = {
            "channel": {
                "type": "whatsapp",
                "identifier": self.service.user.channel_identifier,
                "metadata": {}
            },
            "flow_data": {
                "id": "user_state",
                "step": 0,
                "data": {
                    "flow_type": "auth",
                    "_validation_context": {},
                    "_validation_state": {}
                },
                "_previous_data": {}
            },
            # Preserve existing state data
            "member_id": current_state.get("member_id"),
            "account_id": current_state.get("account_id"),
            "profile": current_state.get("profile", {}),
            "authenticated": current_state.get("authenticated", False),
            "jwt_token": current_state.get("jwt_token"),
            "_validation_context": {},
            "_validation_state": {},
            "_last_updated": audit.get_current_timestamp()
        }

        # Log state transition
        audit.log_state_transition(
            "auth_handler",
            current_state,
            new_state,
            "success"
        )

        # Update state
        self.service.user.state.update_state(new_state, "greeting")

        # Log state after update
        logger.debug(f"State after update in handle_hi: {self.service.user.state.state}")

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
