"""State management and transitions for WhatsApp messages"""
import logging
from typing import Any, Dict, Optional

from core.utils.flow_audit import FlowAuditLogger
from core.messaging.flow import Flow
from ...state_manager import StateManager
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateHandler:
    """Handles state management and transitions"""

    def __init__(self, service: Any):
        self.service = service

    def prepare_flow_start(self, clear_menu: bool = True) -> Optional[WhatsAppMessage]:
        """Prepare state for starting a new flow"""
        current_state = self.service.user.state.state or {}
        new_state = StateManager.prepare_state_update(
            current_state,
            clear_flow=True,
            mobile_number=self.service.user.mobile_number
        )

        error = StateManager.validate_and_update(
            self.service.user.state,
            new_state,
            current_state,
            "clear_flow_menu_action" if clear_menu else "flow_start",
            self.service.user.mobile_number
        )
        return error

    def handle_error_state(self, error_message: str) -> WhatsAppMessage:
        """Handle error state and return error message"""
        current_state = self.service.user.state.state or {}
        error_state = StateManager.prepare_state_update(
            current_state,
            clear_flow=True,
            mobile_number=self.service.user.mobile_number
        )

        StateManager.validate_and_update(
            self.service.user.state,
            error_state,
            current_state,
            "flow_error",
            self.service.user.mobile_number
        )

        return WhatsAppMessage.create_text(
            self.service.user.mobile_number,
            f"❌ {error_message}"
        )

    def handle_invalid_input_state(
        self,
        flow: Flow,
        flow_type: str,
        kwargs: Dict
    ) -> Optional[WhatsAppMessage]:
        """Handle invalid input state update"""
        current_state = self.service.user.state.state or {}
        error_state = StateManager.prepare_state_update(
            current_state,
            flow_data={
                **flow.get_state(),
                "flow_type": flow_type,
                "kwargs": kwargs,
                "_validation_error": True
            },
            mobile_number=self.service.user.mobile_number
        )

        return StateManager.validate_and_update(
            self.service.user.state,
            error_state,
            current_state,
            "flow_validation_error",
            self.service.user.mobile_number
        )

    def handle_flow_completion(self, clear_flow: bool = True) -> Optional[WhatsAppMessage]:
        """Handle flow completion state update"""
        current_state = self.service.user.state.state or {}
        new_state = StateManager.prepare_state_update(
            current_state,
            clear_flow=clear_flow,
            mobile_number=self.service.user.mobile_number
        )

        return StateManager.validate_and_update(
            self.service.user.state,
            new_state,
            current_state,
            "flow_complete",
            self.service.user.mobile_number
        )

    def handle_flow_continuation(
        self,
        flow: Flow,
        flow_type: str,
        kwargs: Dict
    ) -> Optional[WhatsAppMessage]:
        """Handle flow continuation state update"""
        current_state = self.service.user.state.state or {}
        flow_state = flow.get_state()

        new_state = StateManager.prepare_state_update(
            current_state,
            flow_data={
                **flow_state,
                "flow_type": flow_type,
                "kwargs": kwargs
            },
            mobile_number=self.service.user.mobile_number
        )

        return StateManager.validate_and_update(
            self.service.user.state,
            new_state,
            current_state,
            "flow_continue",
            self.service.user.mobile_number
        )

    def get_flow_data(self) -> Optional[Dict]:
        """Get current flow data from state"""
        if not self.service.user.state.state:
            return None
        return self.service.user.state.state.get("flow_data")
