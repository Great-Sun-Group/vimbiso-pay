"""State handling and transitions for WhatsApp flows"""
import logging
from typing import Any, Dict, Optional

from core.messaging.flow import Flow, FlowState
from core.utils.flow_audit import FlowAuditLogger

from ...types import WhatsAppMessage
from ...state_manager import StateManager as WhatsAppStateManager

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateHandler:
    """Handles state management and transitions"""

    def __init__(self, service: Any):
        self.service = service

    def prepare_flow_start(
        self,
        clear_menu: bool = True,
        is_greeting: bool = False,
        flow_type: Optional[str] = None,
        channel_identifier: Optional[str] = None,
        **kwargs
    ) -> Optional[WhatsAppMessage]:
        """Prepare state for starting a new flow"""
        try:
            # Get current state
            current_state = self.service.user.state.state or {}

            # Only require member_id for non-greeting flows
            if not is_greeting and not current_state.get("member_id"):
                return WhatsAppMessage.create_text(
                    self.service.user.channel_identifier,
                    "❌ Error: Member ID not found"
                )

            # Update channel info if provided - SINGLE SOURCE OF TRUTH
            if channel_identifier:
                # Create channel data using prepare_state_update
                new_state = WhatsAppStateManager.prepare_state_update(
                    current_state=self.service.user.state.state or {},
                    channel_identifier=channel_identifier
                )
                # Update only the channel info
                self.service.user.state.update_state({
                    "channel": new_state["channel"]
                })

            # Create flow state with member_id from top level state - SINGLE SOURCE OF TRUTH
            flow_state = FlowState.create(
                flow_id=f"{flow_type}_{current_state.get('member_id')}" if flow_type else "user_state",
                member_id=current_state.get("member_id"),
                flow_type=flow_type or "init"
            )

            # Update ONLY flow_data to preserve SINGLE SOURCE OF TRUTH
            self.service.user.state.update_state({
                "flow_data": flow_state.to_dict()
            })

            return None

        except Exception as e:
            logger.error(f"Error preparing flow start: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def handle_flow_completion(self, clear_flow: bool = True) -> Optional[WhatsAppMessage]:
        """Handle flow completion state update"""
        try:
            if clear_flow:
                # Update ONLY flow_data
                self.service.user.state.update_state({
                    "flow_data": None
                })
            return None

        except Exception as e:
            logger.error(f"Error handling flow completion: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def handle_flow_continuation(
        self,
        flow: Flow,
        flow_type: str,
        kwargs: Dict[str, Any]
    ) -> Optional[WhatsAppMessage]:
        """Handle flow continuation state update"""
        try:
            # Get flow state
            flow_state = flow.get_state()

            # Update ONLY flow_data
            self.service.user.state.update_state({
                "flow_data": flow_state.to_dict()
            })

            return None

        except Exception as e:
            logger.error(f"Error handling flow continuation: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def handle_error_state(self, error_message: str) -> WhatsAppMessage:
        """Handle error state and return error message"""
        try:
            # Get current state
            current_state = self.service.user.state.state or {}

            # Log error with context
            audit.log_flow_event(
                "bot_service",
                "error_state",
                None,
                {
                    "error": error_message,
                    "member_id": current_state.get("member_id"),
                    "channel": current_state.get("channel")
                },
                "failure"
            )

            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {error_message}"
            )

        except Exception as e:
            logger.error(f"Error handling error state: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def handle_invalid_input_state(
        self,
        error_message: str,
        flow_step_id: Optional[str] = None
    ) -> WhatsAppMessage:
        """Handle invalid input state and return error message"""
        try:
            # Get current state
            current_state = self.service.user.state.state or {}

            # Log error with context
            audit.log_flow_event(
                "bot_service",
                "invalid_input",
                flow_step_id,
                {
                    "error": error_message,
                    "member_id": current_state.get("member_id"),
                    "channel": current_state.get("channel")
                },
                "failure"
            )

            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Invalid input: {error_message}"
            )

        except Exception as e:
            logger.error(f"Error handling invalid input: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def get_flow_data(self) -> Optional[Dict]:
        """Get current flow data from state"""
        state = self.service.user.state.state
        if not state or not isinstance(state, dict):
            return None

        return state.get("flow_data")
